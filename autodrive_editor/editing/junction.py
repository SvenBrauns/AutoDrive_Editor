"""Junction template: where a yard road meets a public road.

One-way curves lead in from each road lane to the junction node and out from it to each lane;
the stem into the yard starts at the junction node. Each curve leaves or joins its lane
tangentially at the yard radius, so it works on straight and curved roads, with two one-way lanes
(as from the AI scan) or one two-way road. Where a curve is blocked on the drivability map, other
places along the lane are tried, then tighter radii down to MIN_RADIUS, then the route finder; a
curve that still does not fit is left out and listed.

Headings are in radians in the x-z plane; as z points south on the map, a rising heading is a
turn to the right.
"""

import math
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from itertools import pairwise

from autodrive_editor.editing.commands.add_route import AddRouteCommand
from autodrive_editor.editing.dubins import Pose, shortest_path
from autodrive_editor.editing.path_shapes import spaced_points
from autodrive_editor.editing.route_finder import Grid, Route, RouteRequest, Vehicle
from autodrive_editor.file_io.navigation_costmap import NavigationCostmap
from autodrive_editor.i18n import tr
from autodrive_editor.model.autodrive_data import AutoDriveData, NodeData
from autodrive_editor.model.connections import (
    CONNECTION_STATES,
    NO_CONNECTION,
    ConnectionType,
    is_reverse_connection,
    read_connection_state,
)

Point = tuple[float, float]

# Curves tighten in RADIUS_STEP steps down to MIN_RADIUS where the yard radius does not fit.
MIN_RADIUS = 4.0
RADIUS_STEP = 1.0
# Places where a curve leaves or joins its lane are tried every LEAVE_STEP metres up to
# ALONG_ROAD from the junction, and lanes are followed that far plus the room for a curve.
ALONG_ROAD = 25.0
LEAVE_STEP = 1.0
# An existing lane node this close to such a place is used instead of a new one.
SNAP = 1.0
# The lane in the other direction of a two-lane road lies this close.
OPPOSITE_LANE = 12.0
# A curve turns at most this much more than the angle between lane and stem (no loops).
EXTRA_TURN = math.radians(30)
# Around the junction node and the curve's road end, blocked cells do not count: the junction
# may lie under a roof, and roads run close to fences.
FREE_RADIUS = 3.0
# Nodes on a curve are at most this many degrees of turn apart.
NODE_TURN = math.radians(22.5)
# Curve points this close to the line behind the junction lie on it, in metres.
STEM_TOLERANCE = 0.01
# Points checked along a curve, in metres.
SAMPLE = 0.5


class CurveKind(Enum):
    IN = "in"
    OUT = "out"


@dataclass(frozen=True)
class RoadLane:
    """Part of a road lane near the junction: its node IDs and positions in driving order."""

    node_ids: tuple[int, ...]
    points: tuple[Point, ...]


@dataclass(frozen=True)
class RoadEnd:
    """Where a curve leaves or joins its lane: an existing node, or a point on the connection
    from lane node `index` to the next one."""

    point: Point
    node_id: int | None = None
    index: int | None = None


@dataclass(frozen=True)
class Curve:
    kind: CurveKind
    lane: RoadLane
    road_end: RoadEnd
    # From the road end to the junction (IN) or from the junction to the road end (OUT).
    points: tuple[Point, ...]
    radius: float
    # Built by the route finder, not as a Dubins path.
    searched: bool = False


@dataclass
class JunctionPlan:
    curves: list[Curve]
    # The curves that do not fit, as text for the user.
    missing: list[str]


def road_lanes(autodrive_data: AutoDriveData, source_id: int, target_id: int) -> list[RoadLane]:
    """The lanes of the road with the connection: a two-way road gives its lane each way, a
    one-way lane gives itself and the nearest lane the other way within OPPOSITE_LANE, if any."""

    nodes = autodrive_data.nodes
    source, target = nodes[source_id], nodes[target_id]
    lane = _follow(autodrive_data, source_id, target_id)

    if source_id in target.outgoing:
        return [lane, _reversed(lane)]

    foot = ((source.x + target.x) / 2, (source.z + target.z) / 2)
    heading = math.atan2(target.z - source.z, target.x - source.x)
    best = None

    for node in nodes.values():
        if math.hypot(node.x - foot[0], node.z - foot[1]) > OPPOSITE_LANE + 20:
            continue

        for other_id in node.outgoing:
            other = nodes.get(other_id)

            if other is None or {node.node_id, other_id} & set(lane.node_ids):
                continue

            if is_reverse_connection(node, other):
                continue

            other_heading = math.atan2(other.z - node.z, other.x - node.x)

            if math.cos(other_heading - heading) > -0.7:
                continue

            distance = _distance_to_segment(foot, (node.x, node.z), (other.x, other.z))

            if distance <= OPPOSITE_LANE and (best is None or distance < best[0]):
                best = (distance, node.node_id, other_id)

    if best is None:
        return [lane]

    return [lane, _follow(autodrive_data, best[1], best[2])]


def junction_distance(lanes: list[RoadLane], foot: Point, heading: float, radius: float) -> float:
    """How far from `foot` along the heading the curves of a junction meet: one radius beyond
    the farthest lane that line crosses."""

    dx, dz = math.cos(heading), math.sin(heading)
    farthest = 0.0

    for lane in lanes:
        for (ax, az), (bx, bz) in pairwise(lane.points):
            ex, ez = bx - ax, bz - az
            denominator = dx * ez - dz * ex

            if abs(denominator) < 1e-9:
                continue

            # Crossing at foot + t * direction = a + u * (b - a).
            t = ((ax - foot[0]) * ez - (az - foot[1]) * ex) / denominator
            u = ((ax - foot[0]) * dz - (az - foot[1]) * dx) / denominator

            if 0 <= u <= 1:
                farthest = max(farthest, t)

    return farthest + radius


def plan_junction(
    lanes: list[RoadLane],
    junction: Pose,
    kinds: tuple[CurveKind, ...],
    radius: float,
    costmap: NavigationCostmap | None,
    vehicle: Vehicle,
    marker_ids: frozenset[int] = frozenset(),
    find_route: Callable[[RouteRequest], Route | None] | None = None,
) -> JunctionPlan:
    """The curves of each kind between each lane and the junction, whose heading points into
    the yard. Curves avoid blocked cells (see FREE_RADIUS) and never end on a marker node."""

    checker = _BlockedCheck(costmap, junction, radius, vehicle)
    plan = JunctionPlan([], [])

    for kind in kinds:
        for lane in lanes:
            curve = _fit(lane, kind, junction, radius, checker, marker_ids)

            if curve is None and find_route is not None:
                curve = _searched(lane, kind, junction, radius, marker_ids, find_route)

            if curve is None:
                plan.missing.append(_missing_text(lane, kind, junction))
            else:
                plan.curves.append(curve)

    return plan


def junction_command(
    autodrive_data: AutoDriveData,
    plan: JunctionPlan,
    junction: Pose,
    spacing: float,
    height_for_new_node: Callable[[AutoDriveData, float, float], float],
    junction_id: int | None = None,
) -> AddRouteCommand:
    """The edit that adds the curves: a new junction node unless `junction_id` is given, new
    nodes along each curve, and the lane connections split where a curve leaves or joins one.
    Curve ends on the same connection closer than SNAP share a node. Curves that end along the
    stem line share its nodes from where they reach it; a piece used both in and out is two-way."""

    next_id = max(autodrive_data.nodes, default=0) + 1
    new_nodes: list[NodeData] = []

    def new_node(point: Point) -> int:
        nonlocal next_id
        y = height_for_new_node(autodrive_data, *point)
        new_nodes.append(NodeData(next_id, point[0], y, point[1]))
        next_id += 1

        return next_id - 1

    if junction_id is None:
        junction_id = new_node(junction[:2])

    regular = CONNECTION_STATES[ConnectionType.REGULAR]
    # New nodes on lane connections, per connection (source, target): (fraction, point, id).
    splits: dict[tuple[int, int], list[tuple[float, Point, int]]] = {}
    # Per curve: its own points from the road to the stem line, and where it reaches the line.
    parts = [_stem_part(curve, junction) for curve in plan.curves]
    stem = _stem_nodes(junction, parts, spacing, new_node, junction_id)
    connections = []

    for curve, (points, back) in zip(plan.curves, parts, strict=True):
        road_id = _road_end_id(curve, splits, new_node)
        spaced = spaced_points(points, min(spacing, curve.radius * NODE_TURN))
        chain = [road_id, *(new_node(point) for point in spaced[1:-1]), stem[back]]

        if curve.kind == CurveKind.OUT:
            chain.reverse()

        connections += [(a, b, regular) for a, b in pairwise(chain)]

    connections += _stem_connections(plan, parts, stem)

    for (source_id, target_id), points in splits.items():
        state = read_connection_state(autodrive_data, source_id, target_id)
        chain = [source_id, *(node_id for _, _, node_id in sorted(points)), target_id]
        connections.append((source_id, target_id, NO_CONNECTION))
        connections += [(a, b, state) for a, b in pairwise(chain)]

    return AddRouteCommand(tr("Junction"), autodrive_data, new_nodes, connections)


def _stem_part(curve: Curve, junction: Pose) -> tuple[list[Point], float]:
    """The curve's points from the road to where it reaches the line behind the junction (along
    its heading, towards the road), and the distance of that point from the junction, rounded
    to SNAP. Curves that do not end along that line reach it at the junction."""

    points = list(curve.points if curve.kind == CurveKind.IN else reversed(curve.points))
    x, z, heading = junction
    dx, dz = math.cos(heading), math.sin(heading)
    index = len(points) - 1

    while index > 0:
        px, pz = points[index - 1]
        back = (x - px) * dx + (z - pz) * dz

        if abs((px - x) * dz - (pz - z) * dx) > STEM_TOLERANCE or back < -1e-6:
            break

        index -= 1

    back = SNAP * round(((x - points[index][0]) * dx + (z - points[index][1]) * dz) / SNAP)

    if back <= 0 or index == 0:
        return points, 0.0

    return [*points[:index], (x - back * dx, z - back * dz)], back


def _stem_nodes(
    junction: Pose,
    parts: list[tuple[list[Point], float]],
    spacing: float,
    new_node: Callable[[Point], int],
    junction_id: int,
) -> dict[float, int]:
    """Node IDs on the line behind the junction by distance from it: the junction, a node where
    each curve reaches the line, and nodes between them at most `spacing` apart."""

    x, z, heading = junction
    dx, dz = math.cos(heading), math.sin(heading)
    distances = sorted({back for _, back in parts} | {0.0})
    stem = {0.0: junction_id}

    for near, far in pairwise(distances):
        count = math.ceil((far - near) / spacing)

        for step in range(1, count + 1):
            back = far if step == count else near + (far - near) * step / count
            stem[back] = new_node((x - back * dx, z - back * dz))

    return stem


def _stem_connections(
    plan: JunctionPlan, parts: list[tuple[list[Point], float]], stem: dict[float, int]
) -> list:
    """Connections along the line behind the junction: towards it where curves in use them,
    away from it where curves out do, two-way where both do."""

    connections = []

    for near, far in pairwise(sorted(stem)):
        used_in = any(
            curve.kind == CurveKind.IN and back >= far
            for curve, (_, back) in zip(plan.curves, parts, strict=True)
        )
        used_out = any(
            curve.kind == CurveKind.OUT and back >= far
            for curve, (_, back) in zip(plan.curves, parts, strict=True)
        )
        if used_in and used_out:
            connections.append((stem[far], stem[near], CONNECTION_STATES[ConnectionType.DUAL]))
        elif used_in:
            connections.append((stem[far], stem[near], CONNECTION_STATES[ConnectionType.REGULAR]))
        elif used_out:
            connections.append((stem[near], stem[far], CONNECTION_STATES[ConnectionType.REGULAR]))

    return connections


def _road_end_id(curve: Curve, splits: dict, new_node: Callable[[Point], int]) -> int:
    end = curve.road_end

    if end.node_id is not None:
        return end.node_id

    source_id, target_id = curve.lane.node_ids[end.index], curve.lane.node_ids[end.index + 1]
    key = (source_id, target_id)

    if key not in splits and (target_id, source_id) in splits:
        key = (target_id, source_id)

    points = splits.setdefault(key, [])

    for _, point, node_id in points:
        if math.dist(point, end.point) < SNAP:
            return node_id

    a, b = curve.lane.points[end.index], curve.lane.points[end.index + 1]

    if key != (source_id, target_id):
        a, b = b, a

    fraction = math.dist(a, end.point) / max(math.dist(a, b), 1e-9)
    node_id = new_node(end.point)
    points.append((fraction, end.point, node_id))

    return node_id


def _fit(
    lane: RoadLane,
    kind: CurveKind,
    junction: Pose,
    radius: float,
    checker: "_BlockedCheck",
    marker_ids: frozenset[int],
) -> Curve | None:
    """The shortest clear Dubins curve between the lane and the junction, at the largest radius
    from `radius` down to MIN_RADIUS that has one."""

    places = _places(lane, junction, marker_ids)
    current = radius

    while current >= MIN_RADIUS - 1e-9:
        paths = []

        for end, heading in places:
            path = _curve_path(kind, end.point, heading, junction, current)

            if path is not None:
                paths.append((path.length, end, path))

        for _, end, path in sorted(paths, key=lambda item: item[0]):
            points = [pose[:2] for pose in path.sample(SAMPLE)]

            if checker.is_clear(points, end.point):
                if kind == CurveKind.IN:
                    points[0], points[-1] = end.point, junction[:2]
                else:
                    points[0], points[-1] = junction[:2], end.point

                return Curve(kind, lane, end, tuple(points), current)

        current -= RADIUS_STEP

    return None


def _curve_path(kind: CurveKind, point: Point, lane_heading: float, junction: Pose, radius: float):
    """The Dubins path of the curve, or None if it turns much more than needed (a loop)."""

    if kind == CurveKind.IN:
        start, goal = (*point, lane_heading), junction
    else:
        start, goal = (junction[0], junction[1], junction[2] + math.pi), (*point, lane_heading)

    path = shortest_path(start, goal, radius)

    if path is None:
        return None

    needed = abs(math.remainder(goal[2] - start[2], math.tau))
    turned = sum(
        length for letter, length in zip(path.word, path.lengths, strict=True) if letter != "S"
    )

    return path if turned / radius <= needed + EXTRA_TURN else None


def _places(
    lane: RoadLane, junction: Pose, marker_ids: frozenset[int]
) -> list[tuple[RoadEnd, float]]:
    """Places along the lane within ALONG_ROAD of the junction's foot, every LEAVE_STEP metres,
    each with the lane heading there. A place within SNAP of a lane node becomes that node,
    unless it carries a marker or starts or ends the lane part."""

    lengths = [0.0]

    for a, b in pairwise(lane.points):
        lengths.append(lengths[-1] + math.dist(a, b))

    foot = _arc_length(lane, junction[:2], lengths)
    places = []
    seen_nodes = set()
    count = math.floor(ALONG_ROAD / LEAVE_STEP)

    for step in range(-count, count + 1):
        along = foot + step * LEAVE_STEP

        if not 0 < along < lengths[-1]:
            continue

        index = max(i for i in range(len(lengths) - 1) if lengths[i] <= along)
        snapped = None

        for node_index in (index, index + 1):
            node_id = lane.node_ids[node_index]

            if (
                0 < node_index < len(lane.node_ids) - 1
                and abs(lengths[node_index] - along) < SNAP
                and node_id not in marker_ids
            ):
                snapped = node_index

        if snapped is not None:
            if snapped in seen_nodes:
                continue

            seen_nodes.add(snapped)
            point = lane.points[snapped]
            before = _heading(lane.points[snapped - 1], point)
            after = _heading(point, lane.points[snapped + 1])
            heading = before + math.remainder(after - before, math.tau) / 2
            places.append((RoadEnd(point, node_id=lane.node_ids[snapped]), heading))
            continue

        a, b = lane.points[index], lane.points[index + 1]
        fraction = (along - lengths[index]) / max(lengths[index + 1] - lengths[index], 1e-9)
        point = (a[0] + fraction * (b[0] - a[0]), a[1] + fraction * (b[1] - a[1]))
        places.append((RoadEnd(point, index=index), _heading(a, b)))

    return places


def _searched(
    lane: RoadLane,
    kind: CurveKind,
    junction: Pose,
    radius: float,
    marker_ids: frozenset[int],
    find_route: Callable[[RouteRequest], Route | None],
) -> Curve | None:
    """The curve built by the route finder from the place on the lane where the shortest Dubins
    curve would leave or join it."""

    best = None

    for end, heading in _places(lane, junction, marker_ids):
        path = _curve_path(kind, end.point, heading, junction, radius)

        if path is not None and (best is None or path.length < best[0]):
            best = (path.length, end, heading)

    if best is None:
        return None

    _, end, heading = best

    if kind == CurveKind.IN:
        request = RouteRequest(
            (end.point, junction[:2]), (heading,), (junction[2],), turning_radius=radius
        )
    else:
        request = RouteRequest(
            (junction[:2], end.point), (junction[2] + math.pi,), (heading,), turning_radius=radius
        )

    route = find_route(request)

    if route is None or not route.is_clear:
        return None

    return Curve(kind, lane, end, tuple(route.points), radius, searched=True)


def _missing_text(lane: RoadLane, kind: CurveKind, junction: Pose) -> str:
    """E.g. "No left turn in from the north"."""

    lane_heading = _heading(lane.points[0], lane.points[-1])

    if kind == CurveKind.IN:
        turn = math.remainder(junction[2] - lane_heading, math.tau)
        direction = _compass(lane_heading + math.pi)
        text = (
            tr("No right turn in from the {direction}")
            if turn > 0
            else tr("No left turn in from the {direction}")
        )
    else:
        turn = math.remainder(lane_heading - junction[2] - math.pi, math.tau)
        direction = _compass(lane_heading)
        text = (
            tr("No right turn out to the {direction}")
            if turn > 0
            else tr("No left turn out to the {direction}")
        )

    return text.format(direction=direction)


def _compass(heading: float) -> str:
    """The compass direction of the heading on the map (x east, z south)."""

    names = (tr("east"), tr("south"), tr("west"), tr("north"))

    return names[round(heading / (math.pi / 2)) % 4]


class _BlockedCheck:
    """Whether curve points stay off blocked cells and their safety distance."""

    def __init__(
        self, costmap: NavigationCostmap | None, junction: Pose, radius: float, vehicle: Vehicle
    ):
        self.junction = junction[:2]
        self.grid = None

        if costmap is None:
            return

        margin = ALONG_ROAD + 3 * radius + OPPOSITE_LANE
        half_width, half_height = costmap.width / 2, costmap.height / 2
        x, z = self.junction
        bounds = (
            max(0, math.floor(x - margin + half_width)),
            max(0, math.floor(z - margin + half_height)),
            min(costmap.width, math.ceil(x + margin + half_width)),
            min(costmap.height, math.ceil(z + margin + half_height)),
        )
        self.grid = Grid(costmap, bounds, vehicle.width / 2 + vehicle.margin)

    def is_clear(self, points: list[Point], road_point: Point) -> bool:
        if self.grid is None:
            return True

        for point in points:
            if (
                math.dist(point, self.junction) <= FREE_RADIUS
                or math.dist(point, road_point) <= FREE_RADIUS
            ):
                continue

            index = self.grid.index(*point)

            if index is None or self.grid.blocked[index]:
                return False

        return True


def _follow(autodrive_data: AutoDriveData, source_id: int, target_id: int) -> RoadLane:
    """The lane through the connection, followed both ways while it goes on about straight,
    until ALONG_ROAD plus room for a curve beyond the connection."""

    nodes = autodrive_data.nodes
    reach = ALONG_ROAD + 4 * MIN_RADIUS + 20
    ahead = _walk(nodes, source_id, target_id, reach, forward=True)
    behind = _walk(nodes, target_id, source_id, reach, forward=False)
    node_ids = [*reversed(behind), source_id, target_id, *ahead]

    return RoadLane(tuple(node_ids), tuple((nodes[i].x, nodes[i].z) for i in node_ids))


def _walk(nodes: dict, previous_id: int, current_id: int, reach: float, forward: bool) -> list[int]:
    """Node IDs after `current_id` going on from `previous_id` along driving connections (forward)
    or against them, the straightest way at forks, until `reach` metres."""

    walked = 0.0
    result = []
    seen = {previous_id, current_id}

    while walked < reach:
        previous, current = nodes[previous_id], nodes[current_id]
        heading = math.atan2(current.z - previous.z, current.x - previous.x)
        candidates = current.outgoing if forward else current.incoming
        best = None

        for other_id in candidates:
            other = nodes.get(other_id)

            if other is None or other_id in seen:
                continue

            # Driven connections only, not reverse ones.
            if current_id not in (other.incoming if forward else other.outgoing):
                continue

            turn = abs(
                math.remainder(
                    math.atan2(other.z - current.z, other.x - current.x) - heading, math.tau
                )
            )

            if turn < math.radians(60) and (best is None or turn < best[0]):
                best = (turn, other_id)

        if best is None:
            break

        walked += math.dist((current.x, current.z), (nodes[best[1]].x, nodes[best[1]].z))
        previous_id, current_id = current_id, best[1]
        seen.add(current_id)
        result.append(current_id)

    return result


def _reversed(lane: RoadLane) -> RoadLane:
    return RoadLane(lane.node_ids[::-1], lane.points[::-1])


def _arc_length(lane: RoadLane, point: Point, lengths: list[float]) -> float:
    """Distance along the lane to the lane point closest to `point`."""

    best = None

    for index, (a, b) in enumerate(pairwise(lane.points)):
        t = _segment_fraction(point, a, b)
        foot = (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]))
        distance = math.dist(point, foot)

        if best is None or distance < best[0]:
            best = (distance, lengths[index] + t * (lengths[index + 1] - lengths[index]))

    return best[1]


def _segment_fraction(point: Point, a: Point, b: Point) -> float:
    abx, abz = b[0] - a[0], b[1] - a[1]
    length_squared = abx * abx + abz * abz

    if length_squared == 0:
        return 0.0

    return min(max(((point[0] - a[0]) * abx + (point[1] - a[1]) * abz) / length_squared, 0.0), 1.0)


def _distance_to_segment(point: Point, a: Point, b: Point) -> float:
    t = _segment_fraction(point, a, b)

    return math.dist(point, (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])))


def _heading(a: Point, b: Point) -> float:
    return math.atan2(b[1] - a[1], b[0] - a[0])
