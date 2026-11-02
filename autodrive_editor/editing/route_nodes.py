"""Turns the points of a found route into nodes and connections.

Where the route runs along a planned lane, it uses the lane's nodes instead of new ones. Where it
runs against the lane's direction closer than a lane width, the lane becomes dual there: the way
back shares the lane because there was no room for its own.
"""

import math
from dataclasses import dataclass
from itertools import pairwise

from autodrive_editor.editing.route_finder import Point
from autodrive_editor.model.autodrive_data import AutoDriveData
from autodrive_editor.model.connections import (
    CONNECTION_STATES,
    ConnectionState,
    ConnectionType,
)

# Route points this close to a lane and this parallel to it run along the lane.
SNAP_DISTANCE = 1.5
SNAP_ALIGNMENT = 0.9
# Shorter stretches along a lane get their own nodes.
MIN_SHARED_LENGTH = 3.0
# AutoDrive's recording rule: how far a new node may lie from the last one, by how many degrees
# the direction turns from the last connection (below the angle, metres). Routes are walked in
# RECORDING_STEP steps like the recorder samples a drive.
RECORDING_LIMITS = (
    (0.5, 12.0),
    (1, 6.0),
    (2, 4.0),
    (4, 3.0),
    (7, 2.0),
    (14, 1.0),
    (27, 0.5),
    (math.inf, 0.25),
)
RECORDING_STEP = 0.25


@dataclass(frozen=True)
class PlannedLane:
    """A planned connection that routes can share, from source to target."""

    source_id: int
    target_id: int
    source: Point
    target: Point


def planned_lanes(autodrive_data: AutoDriveData, node_ids: set[int]) -> list[PlannedLane]:
    """The connections between the given nodes in their driving direction; a dual connection
    gives a lane each way. Reverse connections are left out, AutoDrive drives them backwards."""

    lanes = []

    for node_id in node_ids:
        node = autodrive_data.nodes.get(node_id)

        if node is None:
            continue

        for target_id in node.outgoing:
            target = autodrive_data.nodes.get(target_id)

            if target is None or target_id not in node_ids or node_id not in target.incoming:
                continue

            lanes.append(PlannedLane(node_id, target_id, (node.x, node.z), (target.x, target.z)))

    return lanes


def node_headings(autodrive_data: AutoDriveData, node_id: int) -> tuple[float, ...] | None:
    """The directions a vehicle can drive through the node, in radians: from each incoming node
    and towards each outgoing one. None for a node without connections."""

    node = autodrive_data.nodes[node_id]
    headings = []

    for other_id in node.incoming:
        other = autodrive_data.nodes.get(other_id)

        if other is not None and (other.x, other.z) != (node.x, node.z):
            headings.append(math.atan2(node.z - other.z, node.x - other.x))

    for other_id in node.outgoing:
        other = autodrive_data.nodes.get(other_id)

        if other is not None and (other.x, other.z) != (node.x, node.z):
            headings.append(math.atan2(other.z - node.z, other.x - node.x))

    return tuple(headings) or None


def route_nodes(
    points: list[Point],
    start_id: int,
    goal_id: int,
    positions: dict[int, Point],
    lanes: list[PlannedLane],
    spacing: float,
    lane_width: float = 3.5,
) -> list[int | Point]:
    """The route as a chain in driving order: IDs of existing nodes and positions of new ones.
    `positions` has the position of every node the chain can use: start, goal and lane ends.
    Driving against a lane closer than `lane_width` shares it."""

    shares = [_shared_lane(points, index, lanes, lane_width) for index in range(len(points))]
    _drop_short_shares(points, shares)

    chain: list[int | Point] = [start_id]
    # Route points since the last node of the chain.
    free_points: list[Point] = [positions[start_id]]
    index = 0

    while index < len(points):
        if shares[index] is None:
            free_points.append(points[index])
            index += 1
            continue

        end = index

        while end < len(points) and shares[end] is not None:
            end += 1

        shared_ids = _shared_node_ids(points[index:end], shares[index:end])
        _add_free(chain, free_points, positions[shared_ids[0]], spacing)
        _append(chain, shared_ids)
        free_points = [positions[shared_ids[-1]]]
        index = end

    _add_free(chain, free_points, positions[goal_id], spacing)
    _append(chain, [goal_id])

    return chain


def chain_connections(
    autodrive_data: AutoDriveData, node_ids: list[int]
) -> list[tuple[int, int, ConnectionState]]:
    """The connection each pair of the chain's node IDs needs. Pairs that already have a
    connection in the driving direction stay as they are; pairs connected the other way become
    dual. New nodes are not in the data yet."""

    connections = []

    for source_id, target_id in pairwise(node_ids):
        source = autodrive_data.nodes.get(source_id)
        target = autodrive_data.nodes.get(target_id)

        if source is not None and target is not None:
            if target_id in source.outgoing and source_id in target.incoming:
                continue

            if source_id in target.outgoing and target_id in source.incoming:
                connections.append((source_id, target_id, CONNECTION_STATES[ConnectionType.DUAL]))
                continue

        connections.append((source_id, target_id, CONNECTION_STATES[ConnectionType.REGULAR]))

    return connections


def _shared_lane(points: list[Point], index: int, lanes: list[PlannedLane], lane_width: float):
    """The lane the route point runs along and whether it drives in the lane's direction."""

    before = points[max(0, index - 1)]
    after = points[min(len(points) - 1, index + 1)]
    length = math.dist(before, after)

    if length < 1e-6:
        return None

    direction = ((after[0] - before[0]) / length, (after[1] - before[1]) / length)
    best = None

    for lane in lanes:
        lane_length = math.dist(lane.source, lane.target)

        if lane_length < 1e-6:
            continue

        lane_x = (lane.target[0] - lane.source[0]) / lane_length
        lane_z = (lane.target[1] - lane.source[1]) / lane_length
        alignment = direction[0] * lane_x + direction[1] * lane_z

        if abs(alignment) < SNAP_ALIGNMENT:
            continue

        distance, fraction = _project(points[index], lane.source, lane.target)

        limit = SNAP_DISTANCE if alignment > 0 else lane_width

        if distance <= limit and (best is None or distance < best[0]):
            best = (distance, lane, alignment > 0, fraction)

    return None if best is None else best[1:]


def _drop_short_shares(points: list[Point], shares: list):
    index = 0

    while index < len(shares):
        if shares[index] is None:
            index += 1
            continue

        end = index

        while end < len(shares) and shares[end] is not None:
            end += 1

        length = sum(math.dist(a, b) for a, b in pairwise(points[index:end]))

        if length < MIN_SHARED_LENGTH:
            shares[index:end] = [None] * (end - index)

        index = end


def _shared_node_ids(points: list[Point], shares: list) -> list[int]:
    """The lane nodes a shared stretch passes, in driving order. It joins a lane at the node
    nearer to where it meets the lane and leaves it the same way."""

    ids: list[int] = []
    previous = None

    for lane, forward, _ in shares:
        if (lane, forward) == previous:
            continue

        previous = (lane, forward)
        first, second = (
            (lane.source_id, lane.target_id) if forward else (lane.target_id, lane.source_id)
        )

        if not ids:
            ids.append(first)

        _append(ids, [first, second])

    # Join and leave at the nearer end of the first and last lane.
    _, first_forward, first_fraction = shares[0]
    if (first_fraction >= 0.5) == first_forward and len(ids) > 2:
        ids.pop(0)

    _, last_forward, last_fraction = shares[-1]
    if (last_fraction < 0.5) == last_forward and len(ids) > 2:
        ids.pop()

    return ids


def _append(chain: list, items: list):
    for item in items:
        if not chain or chain[-1] != item:
            chain.append(item)


def _add_free(chain: list, free_points: list[Point], end: Point, spacing: float):
    """New nodes along the free stretch from the last node of the chain to `end`."""

    polyline = []

    for point in [*free_points, end]:
        if not polyline or point != polyline[-1]:
            polyline.append(point)

    if len(polyline) < 2:
        return

    chain.extend(_recorded(polyline, spacing)[1:-1])


def _recorded(polyline: list[Point], spacing: float) -> list[Point]:
    """Points along the polyline, both ends included, the way AutoDrive records a drive: up to
    `spacing` apart where the line runs straight, closer the more it turns. The last point
    before the end moves back where it would be less than half its gap from the end."""

    dense = [polyline[0]]

    for a, b in pairwise(polyline):
        count = max(1, math.ceil(math.dist(a, b) / RECORDING_STEP))
        dense += [_lerp(a, b, i / count) for i in range(1, count + 1)]

    points, indices = [dense[0]], [0]
    heading = _heading(polyline[0], polyline[1])

    for index in range(1, len(dense)):
        last, point = points[-1], dense[index]
        distance = math.dist(last, point)

        if distance < 1e-9:
            continue

        turn = abs(math.degrees(_turn(heading, _heading(last, point))))
        limit = min(spacing, next(metres for angle, metres in RECORDING_LIMITS if turn < angle))

        if distance >= limit and index < len(dense) - 1:
            # Back to where the distance is the limit, between the dense points.
            before = math.dist(last, dense[index - 1])
            fraction = max(0.0, (limit - before) / (distance - before))
            points.append(_lerp(dense[index - 1], point, fraction))
            indices.append(index)
            heading = _heading(last, points[-1])

    points.append(dense[-1])

    if len(points) > 2:
        previous_gap = math.dist(points[-3], points[-2])

        if math.dist(points[-2], points[-1]) < previous_gap / 2:
            between = dense[indices[-2] : -1]
            points[-2] = min(
                between,
                key=lambda p: abs(math.dist(points[-3], p) - math.dist(p, points[-1])),
            )

    return points


def _heading(a: Point, b: Point) -> float:
    return math.atan2(b[1] - a[1], b[0] - a[0])


def _turn(a: float, b: float) -> float:
    return (b - a + math.pi) % math.tau - math.pi


def _lerp(a: Point, b: Point, fraction: float) -> Point:
    return a[0] + (b[0] - a[0]) * fraction, a[1] + (b[1] - a[1]) * fraction


def _project(point: Point, a: Point, b: Point) -> tuple[float, float]:
    """Distance of the point to the segment a–b and the fraction along it of the nearest point."""

    abx, abz = b[0] - a[0], b[1] - a[1]
    length_squared = abx * abx + abz * abz
    fraction = ((point[0] - a[0]) * abx + (point[1] - a[1]) * abz) / length_squared
    fraction = min(max(fraction, 0.0), 1.0)

    return math.hypot(point[0] - a[0] - fraction * abx, point[1] - a[1] - fraction * abz), fraction
