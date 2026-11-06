"""Lanes and markers for the stops of stations.

Each chosen stop gets a straight one-way lane along its heading, with the marker node a little
past the stop, so the trailer stands over the trigger when the tractor stops. The default
heading comes from the drivability map: the lane axis with the most free room through the stop
(for a stop with an AI node: its axis or the one across it), driven so that all stops of a
building circle it the same way and one route can pass them all.
The lane's nodes are subprio, so vehicles only drive over the trigger when it is their
destination. A dragged lane end bends its leg in one arc from the stop; an end dropped on a node
joins it.
"""

import math
import string
from dataclasses import dataclass
from itertools import pairwise

from autodrive_editor.editing.commands.add_route import AddRouteCommand
from autodrive_editor.editing.junctions.junction import stem_poses
from autodrive_editor.editing.path_shapes import spaced_points
from autodrive_editor.editing.planned_piece import PlannedPiece
from autodrive_editor.editing.routes.route_nodes import _recorded
from autodrive_editor.editing.stations.fill_type_names import fill_type_name
from autodrive_editor.file_io.navigation_costmap import BLOCKED_VALUE, NavigationCostmap
from autodrive_editor.file_io.savegame_stations import Stop, StopKind
from autodrive_editor.i18n import tr
from autodrive_editor.model.autodrive_data import SUBPRIO_FLAG, AutoDriveData, MarkerData, NodeData
from autodrive_editor.model.connections import CONNECTION_STATES, ConnectionType

Point = tuple[float, float, float]

# An existing node closer than this (in metres) to a lane node is where the lane would go.
OCCUPIED_DISTANCE = 1.0

# Free room is measured this far from the stop, in metres, and checked on lines this far left and
# right of the lane. The first metres are skipped: some lanes lie under a roof, which is blocked.
REACH = 40.0
HALF_WIDTH = 1.5
SKIPPED = 4.0
# Lane axes tried for a stop without an AI node, in degrees.
AXIS_STEP = 5
# The lane circles the building only if it runs at least this much across the line from the
# building to the stop (sine of the angle); else it heads to the side with more free room.
MIN_CIRCLING = 0.5
# Too close to the building's origin to tell which way the lane circles it, in metres.
MIN_RADIUS = 2.0
# The lane is drawn with points this far apart (in metres) before its nodes are spaced.
LINE_STEP = 0.5
# A click picks every building with a stop this close, in metres.
PICK_RADIUS = 15.0


@dataclass(frozen=True)
class StationSettings:
    """Lane length before the stop and after the marker, the node spacing and how far past the
    stop the marker sits, in metres. The tractor stops at the marker, so the offset puts the
    trailer over the trigger."""

    before: float = 10.0
    after: float = 10.0
    spacing: float = 12.0
    marker: float = 8.0


@dataclass(frozen=True)
class LaneEnd:
    """A dragged lane end: where it lies and the existing node it joins, if any."""

    x: float
    z: float
    node_id: int | None = None


@dataclass(frozen=True)
class StopChoice:
    """A stop to build, with its marker, the map angle of its lane (0° up, 90° right) and its
    dragged ends, if any."""

    stop: Stop
    name: str
    group: str
    heading: float
    start: LaneEnd | None = None
    end: LaneEnd | None = None


# Marker names are patterns with the stop's building, its type, its first fill type, what is done
# there and a number, as in "VK-{building}", "{n:03}-{type}" or "{fill}-{action}". Groups are
# patterns too, without the number.
DEFAULT_PATTERN = "{building} ({type})"
PATTERN_FIELDS = {"building", "type", "fill", "action", "n"}
# Values to try a pattern with.
EXAMPLE_FIELDS = {"building": "Building", "type": "Type", "fill": "Fill", "action": "load"}
# Productions are named as course authors do: "Diesel-abladen" in "prod.Destillerie".
PRODUCTION_RULE = ("{fill}-{action}", "prod.{building}")


@dataclass(frozen=True)
class MarkerRule:
    """How the markers of one stop type are named and grouped."""

    pattern: str
    group: str


def default_marker_rules() -> dict[StopKind, MarkerRule]:
    rules = {kind: MarkerRule(DEFAULT_PATTERN, default_group(kind)) for kind in StopKind}

    return rules | {StopKind.PRODUCTION: MarkerRule(*PRODUCTION_RULE)}


def default_group(kind: StopKind) -> str:
    return {
        StopKind.SELL: tr("Selling points"),
        StopKind.UNLOAD: tr("Unloading points"),
        StopKind.LOAD: tr("Loading points"),
        StopKind.BUY: tr("Buying stations"),
        StopKind.PRODUCTION: tr("Productions"),
        StopKind.ANIMALS: tr("Animals"),
        StopKind.DIESEL: tr("Diesel"),
    }[kind]


def pattern_problem(pattern: str, group: bool = False) -> str | None:
    """What is wrong with a marker name pattern (or a group pattern, which has no {n}), or
    None."""

    try:
        names = {name for _, name, _, _ in string.Formatter().parse(pattern) if name is not None}
        unknown = names - (PATTERN_FIELDS - {"n"} if group else PATTERN_FIELDS)

        if unknown:
            return tr("Unknown placeholder {{{name}}}", name=sorted(unknown)[0])

        if not _format(pattern, EXAMPLE_FIELDS, 1).strip():
            return tr("A marker name pattern must not be empty.")
    except (ValueError, TypeError):
        return tr("The pattern “{pattern}” is not valid.", pattern=pattern)

    return None


def marker_names(
    stops: list[Stop],
    rules: dict[StopKind, MarkerRule],
    taken: set[tuple[str, str]],
    start: int = 1,
) -> list[tuple[str, str]]:
    """(name, group) of each stop's marker by the rule of its type, none taken twice. {n} counts
    per group from start, skipping numbers whose name is taken; without {n} a taken name gets
    the lowest free number from 2. The pattern must be valid (pattern_problem)."""

    taken = set(taken)
    numbers: dict[str, int] = {}
    result = []

    for stop in stops:
        rule = rules[stop.kind]
        fields = _fields(stop)
        group = _format(rule.group, fields, start)

        if "{n" in rule.pattern:
            number = numbers.get(group, start)

            while (_format(rule.pattern, fields, number), group) in taken:
                number += 1

            numbers[group] = number + 1
            name = _format(rule.pattern, fields, number)
        else:
            name = unique_name(_format(rule.pattern, fields, start), group, taken)

        taken.add((name, group))
        result.append((name, group))

    return result


def _fields(stop: Stop) -> dict[str, str]:
    """The placeholders of a stop; {fill} is the building's name for a stop without fill types."""

    building = stop.name.strip()

    return {
        "building": building,
        "type": stop.kind.label,
        "fill": fill_type_name(stop.fill_types[0]) if stop.fill_types else building,
        "action": tr("load") if stop.loads else tr("unload"),
    }


def _format(pattern: str, fields: dict[str, str], number: int) -> str:
    return pattern.format(**fields, n=number).strip()


def unique_name(name: str, group: str, taken: set[tuple[str, str]]) -> str:
    """The name, or the name with the lowest number from 2 that is not taken in the group."""

    candidate = name
    number = 2

    while (candidate, group) in taken:
        candidate = f"{name} {number}"
        number += 1

    return candidate


def lane_points(
    stop: Stop,
    settings: StationSettings,
    heading: float,
    start: LaneEnd | None = None,
    end: LaneEnd | None = None,
) -> tuple[list, int]:
    """The lane's nodes in driving direction and the index of the marker node, which lies
    settings.marker past the stop. A straight lane has nodes at equal distances, a bent one as
    AutoDrive records a drive."""

    y = stop.position[1]
    before, after = lane_line(stop, settings, heading, start, end)
    space = spaced_points if start is None and end is None else _recorded
    first = space(before, settings.spacing) if _length(before) > 0 else [before[-1]]
    second = space(after, settings.spacing)[1:] if _length(after) > 0 else []
    # The marker node exactly at its place, not where the spacing would put it.
    points = [(px, y, pz) for px, pz in first[:-1] + [after[0]] + second]

    return points, len(first) - 1


def lane_line(
    stop: Stop,
    settings: StationSettings,
    heading: float,
    start: LaneEnd | None = None,
    end: LaneEnd | None = None,
) -> tuple[list[tuple[float, float]], list[tuple[float, float]]]:
    """The lane in driving direction as a fine line (x, z), split at the marker: from the start
    to the marker and from the marker to the end. Each leg runs from the stop to its end, straight
    by the settings or, if dragged, in one arc."""

    dx, dz = direction(heading)
    x, _, z = stop.position
    angle = math.atan2(dz, dx)

    if start is None:
        start = LaneEnd(x - dx * settings.before, z - dz * settings.before)

    if end is None:
        length = settings.marker + settings.after
        end = LaneEnd(x + dx * length, z + dz * length)

    behind = _leg((x, z, angle + math.pi), (start.x, start.z))[::-1]
    to_marker, from_marker = _split(_leg((x, z, angle), (end.x, end.z)), settings.marker)

    return behind + to_marker[1:], from_marker


def _leg(pose: tuple[float, float, float], tip: tuple[float, float]) -> list:
    return [(px, pz) for px, pz, _ in stem_poses(pose, tip, LINE_STEP)]


def _split(line: list, distance: float) -> tuple[list, list]:
    """The line up to the distance along it and from there on, both with the point there."""

    if distance <= 0:
        return line[:1], line

    walked = 0.0

    for index, (a, b) in enumerate(pairwise(line)):
        length = math.dist(a, b)

        if walked + length > distance:
            fraction = (distance - walked) / length
            point = (a[0] + fraction * (b[0] - a[0]), a[1] + fraction * (b[1] - a[1]))
            return line[: index + 1] + ([point] if fraction > 0 else []), [
                point,
                *line[index + 1 :],
            ]

        walked += length

    return line, line[-1:]


def _length(line: list) -> float:
    return sum(math.dist(a, b) for a, b in pairwise(line))


def plan_stations(choices: list[StopChoice], settings: StationSettings) -> PlannedPiece:
    piece = PlannedPiece()

    for choice in choices:
        points, marker_index = lane_points(
            choice.stop, settings, choice.heading, choice.start, choice.end
        )
        lane = [piece.add(*point, flag=SUBPRIO_FLAG) for point in points]
        piece.chain(lane)
        piece.markers.append((lane[marker_index], choice.name, choice.group))
        piece.open_ends += [lane[0], lane[-1]]

    return piece


def can_join(autodrive_data: AutoDriveData, node_id: int, at_start: bool) -> bool:
    """Whether a lane end may join the node: the start one that is driven to, the end one that is
    driven from."""

    node = autodrive_data.nodes[node_id]

    return bool(node.incoming if at_start else node.outgoing)


def stations_command(
    autodrive_data: AutoDriveData, choices: list[StopChoice], settings: StationSettings
) -> AddRouteCommand:
    """The edit that adds the lanes and their markers, a joined end on its node."""

    new_nodes, connections, markers = lane_parts(
        choices, settings, max(autodrive_data.nodes, default=0) + 1
    )

    return AddRouteCommand(
        tr("Create station lanes"), autodrive_data, new_nodes, connections, markers
    )


def lane_parts(
    choices: list[StopChoice], settings: StationSettings, next_id: int
) -> tuple[list[NodeData], list, list[MarkerData]]:
    """The new nodes (IDs from next_id on), connections and markers of the lanes."""

    new_nodes, connections, markers = [], [], []
    regular = CONNECTION_STATES[ConnectionType.REGULAR]

    for choice in choices:
        points, marker_index = lane_points(
            choice.stop, settings, choice.heading, choice.start, choice.end
        )
        joined = {
            0: choice.start.node_id if choice.start is not None else None,
            len(points) - 1: choice.end.node_id if choice.end is not None else None,
        }
        lane = []

        for index, (x, y, z) in enumerate(points):
            if joined.get(index) is not None:
                lane.append(joined[index])
                continue

            new_nodes.append(NodeData(next_id, x, y, z, SUBPRIO_FLAG))
            lane.append(next_id)
            next_id += 1

        connections += [(a, b, regular) for a, b in pairwise(lane)]
        markers.append(MarkerData(lane[marker_index], choice.name, choice.group))

    return new_nodes, connections, markers


def occupied(points: list[Point], nodes: list[NodeData], distance=OCCUPIED_DISTANCE) -> bool:
    """Whether an existing node sits where one of the points goes. Lane nodes are always new
    (never merged), so the dialog warns instead."""

    xs, zs = [x for x, _, _ in points], [z for _, _, z in points]
    left, right, top, bottom = min(xs) - distance, max(xs) + distance, min(zs), max(zs)
    near = [n for n in nodes if left <= n.x <= right and top - distance <= n.z <= bottom + distance]

    return any(math.hypot(n.x - x, n.z - z) <= distance for x, _, z in points for n in near)


def building_stops_at(stops: list[Stop], x: float, z: float, tolerance: float) -> list[Stop]:
    """All stops of the buildings picked at the point: each with a stop within PICK_RADIUS (or
    tolerance if larger), as buildings standing together often belong together; else one whose
    stops span an area (grown by tolerance) that contains the point."""

    radius = max(PICK_RADIUS, tolerance)
    near = {stop.unique_id for stop in stops if math.dist((x, z), stop.position[::2]) <= radius}

    if near:
        return [stop for stop in stops if stop.unique_id in near]

    buildings: dict[str, list[Stop]] = {}

    for stop in stops:
        buildings.setdefault(stop.unique_id, []).append(stop)

    for building in buildings.values():
        xs = [stop.position[0] for stop in building]
        zs = [stop.position[2] for stop in building]

        if min(xs) - tolerance <= x <= max(xs) + tolerance:
            if min(zs) - tolerance <= z <= max(zs) + tolerance:
                return building

    return []


def default_heading(stop: Stop, costmap: NavigationCostmap | None) -> float:
    """The lane heading of a stop: the freest axis, circling the building counterclockwise on
    the map. Without a drivability map the axis of the building file is kept."""

    x, _, z = stop.position

    if costmap is None:
        axis = stop.heading
    else:
        if stop.from_ai_node:
            candidates = [stop.heading, stop.heading + 90]
        else:
            candidates = range(0, 180, AXIS_STEP)

        def score(axis: float) -> float:
            ahead, behind = free_reach(costmap, x, z, axis), free_reach(costmap, x, z, axis + 180)
            return 2 * min(ahead, behind) + ahead + behind

        axis = max(candidates, key=score)

    radius_x, radius_z = x - stop.building_position[0], z - stop.building_position[1]
    radius = math.hypot(radius_x, radius_z)
    dx, dz = direction(axis)
    # Below 0 the lane runs counterclockwise around the building on the map (z points down).
    across = (radius_x * dz - radius_z * dx) / radius if radius >= MIN_RADIUS else 0.0

    if abs(across) >= MIN_CIRCLING:
        heading = axis if across < 0 else axis + 180
    elif costmap is not None and free_reach(costmap, x, z, axis + 180) > free_reach(
        costmap, x, z, axis
    ):
        heading = axis + 180
    else:
        heading = axis

    return heading % 360


def free_reach(costmap: NavigationCostmap, x: float, z: float, heading: float) -> float:
    """How far a vehicle could drive from the point along the heading before a blocked cell,
    up to REACH."""

    dx, dz = direction(heading)
    distance = SKIPPED

    while distance < REACH:
        for offset in (-HALF_WIDTH, 0.0, HALF_WIDTH):
            px, pz = x + dx * distance - dz * offset, z + dz * distance + dx * offset

            if costmap.value_at(px, pz) >= BLOCKED_VALUE:
                return distance

        distance += 1.0

    return REACH


def direction(heading: float) -> tuple[float, float]:
    """The (x, z) unit vector of a map angle."""

    angle = math.radians(heading)

    return math.sin(angle), -math.cos(angle)
