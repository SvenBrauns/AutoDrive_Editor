"""Lanes and markers for the stops of stations.

Each chosen stop gets a straight one-way lane along its heading, with a node exactly at the stop
that carries the marker. The default heading comes from the drivability map: the lane axis with
the most free room through the stop (for a stop with an AI node: its axis or the one across it),
driven so that all stops of a building circle it the same way and one route can pass them all.
The lane's nodes are subprio, so vehicles only drive over the trigger when it is their
destination. Connecting the lane ends to the network comes later.
"""

import math
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
    """Lane length before and after the stop and the node spacing, in metres."""

    before: float = 10.0
    after: float = 10.0
    spacing: float = 5.0


@dataclass(frozen=True)
class StopChoice:
    """A stop to build, with its marker and the map angle of its lane (0° up, 90° right)."""

    stop: Stop
    name: str
    group: str
    heading: float


def default_marker_name(stop: Stop) -> str:
    return f"{stop.name.strip()} ({stop.kind.label})"


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


def unique_name(name: str, group: str, taken: set[tuple[str, str]]) -> str:
    """The name, or the name with the lowest number from 2 that is not taken in the group."""

    candidate = name
    number = 2

    while (candidate, group) in taken:
        candidate = f"{name} {number}"
        number += 1

    return candidate


def lane_points(stop: Stop, settings: StationSettings, heading: float) -> tuple[list, int]:
    """The lane's nodes in driving direction and the index of the node at the stop."""

    dx, dz = direction(heading)
    x, y, z = stop.position
    start = (x - dx * settings.before, z - dz * settings.before)
    end = (x + dx * settings.after, z + dz * settings.after)

    before = spaced_points([start, (x, z)], settings.spacing) if settings.before > 0 else [(x, z)]
    after = spaced_points([(x, z), end], settings.spacing)[1:] if settings.after > 0 else []
    # The stop node exactly at the stop, not where the spacing would put it.
    points = [(px, y, pz) for px, pz in before[:-1]] + [(x, y, z)]
    points += [(px, y, pz) for px, pz in after]

    return points, len(before) - 1


def plan_stations(choices: list[StopChoice], settings: StationSettings) -> PlannedPiece:
    piece = PlannedPiece()

    for choice in choices:
        points, stop_index = lane_points(choice.stop, settings, choice.heading)
        lane = [piece.add(*point, flag=SUBPRIO_FLAG) for point in points]
        piece.chain(lane)
        piece.markers.append((lane[stop_index], choice.name, choice.group))
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
