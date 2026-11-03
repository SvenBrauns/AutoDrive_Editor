"""Lanes and markers for the stops of stations.

Each chosen stop gets a straight one-way lane along its heading, with the marker node a little
past the stop, so the trailer stands over the trigger when the tractor stops. The default
heading comes from the drivability map: the lane axis with the most free room through the stop
(for a stop with an AI node: its axis or the one across it), driven so that all stops of a
building circle it the same way and one route can pass them all.
The lane's nodes are subprio, so vehicles only drive over the trigger when it is their
destination. Connecting the lane ends to the network comes later.
"""

import math
import string
from dataclasses import dataclass

from autodrive_editor.editing.path_shapes import spaced_points
from autodrive_editor.editing.planned_piece import PlannedPiece
from autodrive_editor.file_io.navigation_costmap import BLOCKED_VALUE, NavigationCostmap
from autodrive_editor.file_io.savegame_stations import Stop, StopKind
from autodrive_editor.i18n import tr
from autodrive_editor.model.autodrive_data import SUBPRIO_FLAG, NodeData

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


@dataclass(frozen=True)
class StationSettings:
    """Lane length before the stop and after the marker, the node spacing and how far past the
    stop the marker sits, in metres. The tractor stops at the marker, so the offset puts the
    trailer over the trigger. A stop is joined to a road at most `reach` away."""

    before: float = 10.0
    after: float = 10.0
    spacing: float = 12.0
    marker: float = 8.0
    reach: float = 50.0


@dataclass(frozen=True)
class StopChoice:
    """A stop to build, with its marker and the map angle of its lane (0° up, 90° right)."""

    stop: Stop
    name: str
    group: str
    heading: float


# Marker names are patterns with the stop's building, its type and a number, as in "VK-{building}"
# or "{n:03}-{type}".
DEFAULT_PATTERN = "{building} ({type})"
PATTERN_FIELDS = {"building", "type", "n"}


@dataclass(frozen=True)
class MarkerRule:
    """How the markers of one stop type are named and grouped."""

    pattern: str
    group: str


def default_marker_rules() -> dict[StopKind, MarkerRule]:
    return {kind: MarkerRule(DEFAULT_PATTERN, default_group(kind)) for kind in StopKind}


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


def pattern_problem(pattern: str) -> str | None:
    """What is wrong with a marker name pattern, or None."""

    try:
        names = {name for _, name, _, _ in string.Formatter().parse(pattern) if name is not None}
        unknown = names - PATTERN_FIELDS

        if unknown:
            return tr("Unknown placeholder {{{name}}}", name=sorted(unknown)[0])

        if not _format(pattern, "Building", "Type", 1).strip():
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
        building, kind = stop.name.strip(), stop.kind.label

        if "{n" in rule.pattern:
            number = numbers.get(rule.group, start)

            while (_format(rule.pattern, building, kind, number), rule.group) in taken:
                number += 1

            numbers[rule.group] = number + 1
            name = _format(rule.pattern, building, kind, number)
        else:
            name = unique_name(_format(rule.pattern, building, kind, start), rule.group, taken)

        taken.add((name, rule.group))
        result.append((name, rule.group))

    return result


def _format(pattern: str, building: str, kind: str, number: int) -> str:
    return pattern.format(building=building, type=kind, n=number).strip()


def unique_name(name: str, group: str, taken: set[tuple[str, str]]) -> str:
    """The name, or the name with the lowest number from 2 that is not taken in the group."""

    candidate = name
    number = 2

    while (candidate, group) in taken:
        candidate = f"{name} {number}"
        number += 1

    return candidate


def lane_points(stop: Stop, settings: StationSettings, heading: float) -> tuple[list, int]:
    """The lane's nodes in driving direction and the index of the marker node, which lies
    settings.marker past the stop."""

    dx, dz = direction(heading)
    x, y, z = stop.position
    start = (x - dx * settings.before, z - dz * settings.before)
    mx, mz = x + dx * settings.marker, z + dz * settings.marker
    end = (mx + dx * settings.after, mz + dz * settings.after)
    length = settings.before + settings.marker

    before = spaced_points([start, (mx, mz)], settings.spacing) if length > 0 else [(mx, mz)]
    after = spaced_points([(mx, mz), end], settings.spacing)[1:] if settings.after > 0 else []
    # The marker node exactly at its place, not where the spacing would put it.
    points = [(px, y, pz) for px, pz in before[:-1]] + [(mx, y, mz)]
    points += [(px, y, pz) for px, pz in after]

    return points, len(before) - 1


def plan_stations(choices: list[StopChoice], settings: StationSettings) -> PlannedPiece:
    piece = PlannedPiece()

    for choice in choices:
        points, marker_index = lane_points(choice.stop, settings, choice.heading)
        lane = [piece.add(*point, flag=SUBPRIO_FLAG) for point in points]
        piece.chain(lane)
        piece.markers.append((lane[marker_index], choice.name, choice.group))
        piece.open_ends += [lane[0], lane[-1]]

    return piece


def occupied(points: list[Point], nodes: list[NodeData], distance=OCCUPIED_DISTANCE) -> bool:
    """Whether an existing node sits where one of the points goes. Lane nodes are always new
    (never merged), so the dialog warns instead."""

    xs, zs = [x for x, _, _ in points], [z for _, _, z in points]
    left, right, top, bottom = min(xs) - distance, max(xs) + distance, min(zs), max(zs)
    near = [n for n in nodes if left <= n.x <= right and top - distance <= n.z <= bottom + distance]

    return any(math.hypot(n.x - x, n.z - z) <= distance for x, _, z in points for n in near)


def building_stops_at(stops: list[Stop], x: float, z: float, tolerance: float) -> list[Stop]:
    """All stops of the building picked at the point: the one with the closest stop within
    tolerance, else one whose stops span an area (grown by tolerance) that contains the point."""

    near = [stop for stop in stops if math.dist((x, z), stop.position[::2]) <= tolerance]

    if near:
        closest = min(near, key=lambda stop: math.dist((x, z), stop.position[::2]))
        return [stop for stop in stops if stop.unique_id == closest.unique_id]

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
