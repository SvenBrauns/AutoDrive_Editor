"""Stops attached to a drawn yard road (see yard_road): each as a Branch, a Chain or a Back-in bay.

- Branch: a one-way lane of subprio nodes along the stop, which leaves the yard road with a kink
  some metres before the lane and rejoins it after. The lane runs in the road's direction.
- Chain: stops close together share one branch; the lane runs from marker to the next stop.
- Back-in bay: as in sheds, a dual line from the marker outward, a straight stub to drive past
  it and one reverse connection back. Here the line bends towards the road's direction, so the
  stub lies beside the road; the bay is entered from the road and left onto it after the stub.

Stops too far from the road keep their own lane with open ends (Lane).
Points are map positions (x, z); headings in radians as in dubins, stop headings in degrees as
in station_layout.
"""

import bisect
import math
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from itertools import pairwise

from autodrive_editor.editing.commands.add_route import AddRouteCommand
from autodrive_editor.editing.junctions.junction import CurveKind, _turns_little, kinked
from autodrive_editor.editing.planned_piece import PlannedPiece
from autodrive_editor.editing.routes.dubins import advance, shortest_path
from autodrive_editor.editing.stations.station_layout import (
    StationSettings,
    StopChoice,
    can_join,
    direction,
    lane_parts,
)
from autodrive_editor.editing.stations.yard_road import LINE_STEP, YardRoad, length, road_points
from autodrive_editor.file_io.savegame_stations import Stop, StopKind
from autodrive_editor.i18n import tr
from autodrive_editor.model.autodrive_data import (
    REGULAR_FLAG,
    SUBPRIO_FLAG,
    AutoDriveData,
    MarkerData,
    NodeData,
)
from autodrive_editor.model.connections import CONNECTION_STATES, ConnectionType

Point = tuple[float, float]
Pose = tuple[float, float, float]

# Stops farther from the yard road than this (in metres) keep their own lane.
ATTACH_DISTANCE = 30.0
# Stops closer than this along the road share one branch by default.
CHAIN_GAP = 15.0
# How far along the road (in metres) a branch leaves before its lane and rejoins after it:
# preferred first, then farther, then closer.
FORK_TRIES = (*range(15, 41), *range(14, 5, -1))
# A branch leaves or joins the road on an arc only where no straight is left: within this many
# metres of a place the road must not turn.
ARC_CHECK = 1.0
# A bay's stub lies this far beside the road, is this long, and its line has nodes this close.
BAY_SIDE = 6.0
BAY_STUB = 15.0
BAY_STEP = 1.5
# A bay whose line would turn more than this to the road's direction lies along the road.
MAX_BAY_TURN = math.radians(135)


class StopShape(StrEnum):
    BRANCH = "branch"
    CHAIN = "chain"
    BAY = "bay"
    LANE = "lane"

    @property
    def label(self) -> str:
        return {
            StopShape.BRANCH: tr("Branch"),
            StopShape.CHAIN: tr("Chain"),
            StopShape.BAY: tr("Back-in bay"),
            StopShape.LANE: tr("Lane"),
        }[self]


@dataclass(frozen=True)
class YardStop:
    choice: StopChoice
    shape: StopShape


@dataclass
class YardPlan:
    """The road and the attached stops as one piece (points (x, z)), the node indices of the
    road's two ends (a Loop has only the stem's start) and the stops that could not be
    attached, with the reason."""

    piece: PlannedPiece
    ends: tuple[int, int | None]
    problems: list[tuple[StopChoice, str]] = field(default_factory=list)


class _Road:
    """The one-way road as a fine line with distances along it."""

    def __init__(self, road: YardRoad):
        self.line, self.loop = road.road, road.loop
        self.walked = [0.0]

        for a, b in pairwise(self.line):
            self.walked.append(self.walked[-1] + math.dist(a, b))

        self.length = self.walked[-1]

    def foot(self, point: Point) -> tuple[float, float]:
        """Distance along the road to the point's nearest place on it, and the distance off."""

        best = (math.inf, 0.0)

        for index, (a, b) in enumerate(pairwise(self.line)):
            dx, dz = b[0] - a[0], b[1] - a[1]
            step = math.hypot(dx, dz)
            t = ((point[0] - a[0]) * dx + (point[1] - a[1]) * dz) / step**2 if step else 0.0
            t = min(1.0, max(0.0, t))
            off = math.dist(point, (a[0] + t * dx, a[1] + t * dz))

            if off < best[0]:
                best = (off, self.walked[index] + t * step)

        return best[1], best[0]

    def wrapped(self, distance: float) -> float | None:
        if self.loop:
            return distance % self.length

        return distance if 0 <= distance <= self.length else None

    def on_arc(self, distance: float) -> bool:
        """Whether the road turns within ARC_CHECK of the distance."""

        before, after = (self.wrapped(distance + d) for d in (-ARC_CHECK, ARC_CHECK))
        before = distance if before is None else before
        after = distance if after is None else after
        turn = math.remainder(self.pose(after)[2] - self.pose(before)[2], math.tau)

        return abs(turn) > math.radians(0.5)

    def pose(self, distance: float) -> Pose:
        index = min(max(bisect.bisect_right(self.walked, distance) - 1, 0), len(self.line) - 2)
        a, b = self.line[index], self.line[index + 1]
        step = self.walked[index + 1] - self.walked[index]
        t = (distance - self.walked[index]) / step if step else 0.0

        return (
            a[0] + t * (b[0] - a[0]),
            a[1] + t * (b[1] - a[1]),
            math.atan2(b[1] - a[1], b[0] - a[0]),
        )


@dataclass
class _Chain:
    """A run of nodes along a fine line. Its ends are a road distance, the name of a node shared
    with another chain, or None for a new node; markers at distances along the line."""

    line: list[Point]
    kind: ConnectionType
    start: float | str | None
    end: float | str | None
    spacing: float
    markers: list[tuple[float, StopChoice]] = field(default_factory=list)


def default_shapes(stops: list[Stop], road: YardRoad) -> list[StopShape]:
    """Lane for stops too far from the road, a bay for animal barns, a chain for a stop close
    along the road to the one before it, else a branch."""

    ring = _Road(road)
    feet = [ring.foot(_xz(stop)) for stop in stops]
    shapes = [StopShape.LANE] * len(stops)
    previous = None

    for index in sorted(range(len(stops)), key=lambda i: feet[i][0]):
        along, off = feet[index]

        if off > ATTACH_DISTANCE:
            continue

        if stops[index].kind == StopKind.ANIMALS:
            shapes[index] = StopShape.BAY
            continue

        close = previous is not None and along - previous < CHAIN_GAP
        shapes[index] = StopShape.CHAIN if close else StopShape.BRANCH
        previous = along

    return shapes


def plan_yard(
    road: YardRoad, stops: list[YardStop], settings: StationSettings, radius: float
) -> YardPlan:
    """The road with the stops that are not Lane attached to it."""

    ring = _Road(road)
    chains: list[_Chain] = []
    reverses: list[tuple[str, str]] = []
    problems: list[tuple[StopChoice, str]] = []
    units: list[list[StopChoice]] = []
    attached = [stop for stop in stops if stop.shape != StopShape.LANE]
    attached.sort(key=lambda stop: ring.foot(_xz(stop.choice.stop))[0])
    after_unit = False

    for number, stop in enumerate(attached):
        if stop.shape == StopShape.BAY:
            bay = _bay(ring, stop.choice, settings, radius, str(number))

            if isinstance(bay, str):
                problems.append((stop.choice, bay))
            else:
                chains += bay
                reverses.append((f"T{number}", f"S{number}"))

            after_unit = False
        elif stop.shape == StopShape.CHAIN and after_unit:
            units[-1].append(stop.choice)
        else:
            units.append([stop.choice])
            after_unit = True

    for unit in units:
        branch = _branch(ring, unit, settings, radius)

        if isinstance(branch, str):
            problems += [(choice, branch) for choice in unit]
        else:
            chains.append(branch)

    return _build(road, ring, chains, reverses, problems, settings.spacing)


def _build(road, ring, chains, reverses, problems, spacing) -> YardPlan:
    piece = PlannedPiece()
    fixed = [end for chain in chains for end in (chain.start, chain.end) if isinstance(end, float)]
    points = road_points(road.road, spacing, fixed)
    road_walked = _walked(points)
    # A ring ends where it starts, on the same node.
    road_ids = [
        piece.add(*point, flag=REGULAR_FLAG) for point in points[: -1 if road.loop else None]
    ]
    piece.chain([*road_ids, road_ids[0]] if road.loop else road_ids)

    def road_node(distance: float) -> int:
        index = _nearest(road_walked, distance)

        return road_ids[index % len(road_ids)]

    first = road_ids[0]

    if road.stem:
        stem = road_points(road.stem, spacing)
        stem_ids = [piece.add(*point, flag=REGULAR_FLAG) for point in stem[:-1]] + [road_ids[0]]
        piece.chain(stem_ids, ConnectionType.DUAL)
        first = stem_ids[0]

    named: dict[str, int] = {}

    def node(end, point: Point) -> int:
        if isinstance(end, float):
            return road_node(end)

        if isinstance(end, str) and end in named:
            return named[end]

        index = piece.add(*point, flag=SUBPRIO_FLAG)

        if isinstance(end, str):
            named[end] = index

        return index

    for chain in chains:
        points = road_points(chain.line, chain.spacing, [d for d, _ in chain.markers])
        ids = [node(chain.start, points[0])]
        ids += [piece.add(*point, flag=SUBPRIO_FLAG) for point in points[1:-1]]
        ids.append(node(chain.end, points[-1]))
        piece.chain(ids, chain.kind)
        walked = _walked(points)
        piece.markers += [
            (ids[_nearest(walked, d)], choice.name, choice.group) for d, choice in chain.markers
        ]

    for source, target in reverses:
        piece.connect(named[source], named[target], ConnectionType.REVERSE)

    return YardPlan(piece, (first, None if road.loop else road_ids[-1]), problems)


def joined_ends(
    autodrive_data: AutoDriveData,
    corners: list[Point],
    corner_nodes: list[int | None],
    loop: bool,
) -> tuple[list[Point], tuple[int | None, int | None]]:
    """The corners with each end that may join the node it was put on moved onto it, and the
    nodes the road's start and end join. The start node must be driven to (for a Loop's two-way
    stem also driven from), the end node driven from; a Loop has no end."""

    corners = list(corners)
    start, end = corner_nodes[0], None if loop else corner_nodes[-1]

    if start is not None and not (
        can_join(autodrive_data, start, True)
        and (not loop or can_join(autodrive_data, start, False))
    ):
        start = None

    if end is not None and not can_join(autodrive_data, end, False):
        end = None

    for index, node_id in ((0, start), (-1, end)):
        if node_id is not None:
            node = autodrive_data.nodes[node_id]
            corners[index] = (node.x, node.z)

    return corners, (start, end)


def yard_command(
    autodrive_data: AutoDriveData,
    plan: YardPlan,
    joined: tuple[int | None, int | None],
    lanes: list[StopChoice],
    settings: StationSettings,
    height: Callable[[AutoDriveData, float, float], float],
) -> AddRouteCommand:
    """The edit that adds the yard plan, its road ends on the joined nodes, and the stops with
    their own lanes; new yard nodes get their height from `height`."""

    next_id = max(autodrive_data.nodes, default=0) + 1
    new_nodes, connections, markers = lane_parts(lanes, settings, next_id)
    next_id += len(new_nodes)
    piece = plan.piece
    ids = {
        end: node_id for end, node_id in zip(plan.ends, joined, strict=True) if node_id is not None
    }

    for index, ((x, z), flag) in enumerate(zip(piece.points, piece.flags, strict=True)):
        if index not in ids:
            new_nodes.append(NodeData(next_id, x, height(autodrive_data, x, z), z, flag))
            ids[index] = next_id
            next_id += 1

    connections += [(ids[s], ids[t], CONNECTION_STATES[kind]) for s, t, kind in piece.connections]
    markers += [MarkerData(ids[index], name, group) for index, name, group in piece.markers]

    return AddRouteCommand(
        tr("Create station yard"), autodrive_data, new_nodes, connections, markers
    )


def _branch(ring: _Road, unit: list[StopChoice], settings, radius) -> _Chain | str:
    lane = _lane(ring, unit, settings, radius)

    if isinstance(lane, str):
        return lane

    line, markers, start, end = lane
    fork = _fork(ring, start, radius)

    if fork is None:
        return tr("No room to leave the yard road before this stop")

    merge = _merge(ring, end, radius)

    if merge is None:
        return tr("No room to rejoin the yard road after this stop")

    shift = length(fork[1])
    markers = [(d + shift, choice) for d, choice in markers]
    line = fork[1] + line[1:] + merge[1][1:]

    return _Chain(line, ConnectionType.REGULAR, fork[0], merge[0], settings.spacing, markers)


def _lane(ring: _Road, unit: list[StopChoice], settings: StationSettings, radius):
    """The lane past the stops of a branch in the road's direction: the line, its marker
    distances and its start and end poses."""

    line: list[Point] = []
    markers = []
    previous = None

    for choice in unit:
        x, z = _xz(choice.stop)
        dx, dz = _along_road(ring, choice)
        heading = math.atan2(dz, dx)
        marker = (x + dx * settings.marker, z + dz * settings.marker)

        if previous is None:
            line = [(x - dx * settings.before, z - dz * settings.before), (x, z)]
        else:
            path = shortest_path(previous, (x, z, heading), radius)

            if path is None or not _turns_little(path, previous[2], heading, radius):
                return tr("Too close to the stop before it for a chain")

            line += [pose[:2] for pose in path.sample(LINE_STEP)][1:]

        line.append(marker)
        markers.append((length(line), choice))
        previous = (*marker, heading)

    end = (previous[0] + dx * settings.after, previous[1] + dz * settings.after)
    line.append(end)
    start = (*line[0], math.atan2(line[1][1] - line[0][1], line[1][0] - line[0][0]))

    return line, markers, start, (*end, previous[2])


def _bay(ring: _Road, choice: StopChoice, settings, radius, name: str) -> list[_Chain] | str:
    """Dual line from the marker out and round to S beside the road, stub S → T along the road;
    the fork into S and the merge out of T. T → S is the reverse connection (added by the
    caller)."""

    stop = _xz(choice.stop)
    along, _ = ring.foot(stop)
    foot_x, foot_z, road_heading = ring.pose(along)
    dx, dz = direction(choice.heading)

    if dx * (foot_x - stop[0]) + dz * (foot_z - stop[1]) < 0:
        dx, dz = -dx, -dz

    out = math.atan2(dz, dx)
    turn = math.remainder(road_heading - out, math.tau)

    if abs(turn) > MAX_BAY_TURN:
        return tr("The bay would lie along the yard road")

    marker = (stop[0] + dx * settings.marker, stop[1] + dz * settings.marker)
    road_dir = (math.cos(road_heading), math.sin(road_heading))

    def side(point: Point) -> float:
        return road_dir[0] * (point[1] - foot_z) - road_dir[1] * (point[0] - foot_x)

    def round_end(reach: float) -> Pose:
        start = (marker[0] + dx * reach, marker[1] + dz * reach, out)

        return advance(start, math.copysign(1 / radius, turn), abs(turn) * radius)

    sign = math.copysign(1.0, side(stop))
    near, far = side(round_end(0.0)[:2]), side(round_end(1.0)[:2])
    reach = (sign * BAY_SIDE - near) / (far - near) if abs(far - near) > 1e-6 else -1.0

    if reach < 0:
        return tr("No room for a bay between the stop and the yard road")

    bend = (marker[0] + dx * reach, marker[1] + dz * reach, out)
    arc_count = max(1, math.ceil(abs(turn) * radius / LINE_STEP))
    arc = [
        advance(bend, math.copysign(1 / radius, turn), abs(turn) * radius * k / arc_count)[:2]
        for k in range(1, arc_count + 1)
    ]
    s_pose = round_end(reach)
    t_point = (s_pose[0] + road_dir[0] * BAY_STUB, s_pose[1] + road_dir[1] * BAY_STUB)
    fork = _fork(ring, s_pose, radius)
    merge = _merge(ring, (*t_point, road_heading), radius)

    if fork is None or merge is None:
        return tr("No room to leave or rejoin the yard road at this bay")

    s, t = f"S{name}", f"T{name}"
    bay_line = _Chain([marker, bend[:2], *arc], ConnectionType.DUAL, None, s, BAY_STEP)
    bay_line.markers.append((0.0, choice))

    return [
        bay_line,
        _Chain([s_pose[:2], t_point], ConnectionType.REGULAR, s, t, BAY_STEP),
        _Chain(fork[1], ConnectionType.REGULAR, fork[0], s, settings.spacing),
        _Chain(merge[1], ConnectionType.REGULAR, t, merge[0], settings.spacing),
    ]


def _fork(ring: _Road, goal: Pose, radius: float) -> tuple[float, list[Point]] | None:
    """Where on the road a way to the pose leaves, with a kink, and the way."""

    along, _ = ring.foot(goal[:2])

    for distance in _places(ring, [along - back for back in FORK_TRIES]):
        x, z, heading = ring.pose(distance)
        start = (x, z, kinked(CurveKind.IN, (x, z), heading, goal[:2]))
        path = shortest_path(start, goal, radius)

        if path is not None and _turns_little(path, start[2], goal[2], radius):
            return float(distance), [pose[:2] for pose in path.sample(LINE_STEP)]

    return None


def _merge(ring: _Road, start: Pose, radius: float) -> tuple[float, list[Point]] | None:
    """Where on the road a way from the pose rejoins it, with a kink, and the way."""

    along, _ = ring.foot(start[:2])

    for distance in _places(ring, [along + ahead for ahead in FORK_TRIES]):
        x, z, heading = ring.pose(distance)
        goal = (x, z, kinked(CurveKind.OUT, (x, z), heading, start[:2]))
        path = shortest_path(start, goal, radius)

        if path is not None and _turns_little(path, start[2], goal[2], radius):
            return float(distance), [pose[:2] for pose in path.sample(LINE_STEP)]

    return None


def _places(ring: _Road, distances: list[float]) -> list[float]:
    """The distances that lie on the road, those on its straights first (in their order), as
    branches leave and join on straights where they can."""

    on_road = [d for d in map(ring.wrapped, distances) if d is not None]

    return sorted(on_road, key=ring.on_arc)


def _along_road(ring: _Road, choice: StopChoice) -> tuple[float, float]:
    """The stop's lane direction, turned round if it runs against the road."""

    dx, dz = direction(choice.heading)
    heading = ring.pose(ring.foot(_xz(choice.stop))[0])[2]

    if dx * math.cos(heading) + dz * math.sin(heading) < 0:
        return -dx, -dz

    return dx, dz


def _xz(stop: Stop) -> Point:
    return stop.position[0], stop.position[2]


def _walked(points: list[Point]) -> list[float]:
    walked = [0.0]

    for a, b in pairwise(points):
        walked.append(walked[-1] + math.dist(a, b))

    return walked


def _nearest(walked: list[float], distance: float) -> int:
    return min(range(len(walked)), key=lambda index: abs(walked[index] - distance))
