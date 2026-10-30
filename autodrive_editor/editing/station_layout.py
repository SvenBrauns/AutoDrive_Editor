"""Lanes and markers for the stops of stations (docs/generators.md, step 5).

Each chosen stop gets a straight one-way lane along its arrow, with a node exactly at the stop
that carries the marker. The lane's nodes are subprio, so vehicles only drive over the trigger
when it is their destination. Connecting the lane ends to the network comes later.
"""

import math
from dataclasses import dataclass, field

from autodrive_editor.editing.path_shapes import spaced_points
from autodrive_editor.file_io.savegame_stations import Stop, StopKind
from autodrive_editor.i18n import tr
from autodrive_editor.model.autodrive_data import NodeData

Point = tuple[float, float, float]

# An existing node closer than this (in metres) to a lane node is where the lane would go.
OCCUPIED_DISTANCE = 1.0


@dataclass(frozen=True)
class StationSettings:
    """Lane length before and after the stop and the node spacing, in metres."""

    before: float = 10.0
    after: float = 10.0
    spacing: float = 5.0


@dataclass(frozen=True)
class StopChoice:
    """A stop to build, with its marker; turned reverses the lane against the arrow."""

    stop: Stop
    name: str
    group: str
    turned: bool = False


@dataclass
class StationNetwork:
    """Nodes as (x, y, z), one-way connections between their indices, markers as
    (index, name, group), and the lane ends that still need a connection to the network."""

    points: list[Point] = field(default_factory=list)
    connections: list[tuple[int, int]] = field(default_factory=list)
    markers: list[tuple[int, str, str]] = field(default_factory=list)
    open_ends: list[int] = field(default_factory=list)


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


def lane_points(stop: Stop, settings: StationSettings, turned: bool = False) -> tuple[list, int]:
    """The lane's nodes in driving direction and the index of the node at the stop."""

    heading = math.radians(stop.heading + (180 if turned else 0))
    dx, dz = math.sin(heading), -math.cos(heading)
    x, y, z = stop.position
    start = (x - dx * settings.before, z - dz * settings.before)
    end = (x + dx * settings.after, z + dz * settings.after)

    before = spaced_points([start, (x, z)], settings.spacing) if settings.before > 0 else [(x, z)]
    after = spaced_points([(x, z), end], settings.spacing)[1:] if settings.after > 0 else []
    # The stop node exactly at the stop, not where the spacing would put it.
    points = [(px, y, pz) for px, pz in before[:-1]] + [(x, y, z)]
    points += [(px, y, pz) for px, pz in after]

    return points, len(before) - 1


def plan_stations(choices: list[StopChoice], settings: StationSettings) -> StationNetwork:
    network = StationNetwork()

    for choice in choices:
        points, stop_index = lane_points(choice.stop, settings, choice.turned)
        first = len(network.points)
        network.points += points
        network.connections += [(first + i, first + i + 1) for i in range(len(points) - 1)]
        network.markers.append((first + stop_index, choice.name, choice.group))
        network.open_ends += [first, first + len(points) - 1]

    return network


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
