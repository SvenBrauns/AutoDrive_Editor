"""A parallel lane beside selected roads: the selected chains, their offset lines and the nodes of
the new lanes.

Offsets are signed: a positive distance lies to the right of the chain's direction as seen on
the map, a negative one to the left.
"""

import math
from dataclasses import dataclass
from itertools import pairwise

from autodrive_editor.editing.path_shapes import Point, spaced_points
from autodrive_editor.i18n import tr
from autodrive_editor.model.autodrive_data import REGULAR_FLAG, AutoDriveData
from autodrive_editor.model.connections import ConnectionState, read_connection_state


@dataclass(frozen=True)
class ParallelLaneOptions:
    """Settings of the parallel lane tool. The pointer sets the distance and the side."""

    distance: float = 5.5
    opposite: bool = False
    spacing: float = 5.0
    flag: int = REGULAR_FLAG


class ParallelLaneError(ValueError):
    """No parallel lane can be made; the message says why."""


class TightCurveError(ParallelLaneError):
    """The line turns tighter than the offset distance at the point with this index."""

    def __init__(self, index: int):
        super().__init__(f"Tight curve at point {index}")
        self.index = index


@dataclass(frozen=True)
class Chain:
    """Selected nodes connected one after another, in driving direction (dual: from one end), and
    the connection state they all share."""

    node_ids: tuple[int, ...]
    state: ConnectionState


def selected_chains(autodrive_data: AutoDriveData, node_ids) -> list[Chain]:
    """The chains formed by the connections between the selected nodes. Nodes without a selected
    neighbour are left out. Raises ParallelLaneError for a branch, a closed ring or a chain whose
    connections differ in type or direction."""

    nodes = autodrive_data.nodes
    node_ids = set(node_ids)
    neighbors = {
        node_id: (nodes[node_id].incoming | nodes[node_id].outgoing) & node_ids - {node_id}
        for node_id in node_ids
    }

    # Reverse connections are only stored in the source node.
    for node_id in node_ids:
        for target_id in nodes[node_id].outgoing & node_ids - {node_id}:
            neighbors[target_id].add(node_id)

    for node_id in sorted(node_ids):
        if len(neighbors[node_id]) > 2:
            raise ParallelLaneError(tr("Node {node} is a junction of the selection", node=node_id))

    chains, done = [], set()

    for node_id in sorted(node_ids):
        if node_id in done or len(neighbors[node_id]) != 1:
            continue

        run, previous = [node_id], None

        while True:
            following = neighbors[run[-1]] - {previous}

            if not following:
                break

            previous = run[-1]
            run.append(following.pop())

        done.update(run)
        chains.append(_chain(autodrive_data, run))

    if any(neighbors[node_id] and node_id not in done for node_id in node_ids):
        raise ParallelLaneError(tr("The selection forms a closed ring"))

    return chains


def _chain(autodrive_data: AutoDriveData, run: list[int]) -> Chain:
    states = {read_connection_state(autodrive_data, a, b) for a, b in pairwise(run)}

    if len(states) > 1:
        raise ParallelLaneError(
            tr("The connections at node {node} differ in type or direction", node=run[0])
        )

    state = states.pop()

    # Walked against the driving direction: the source entry is at the other end.
    if not state[0]:
        run.reverse()
        state = read_connection_state(autodrive_data, run[0], run[1])

    return Chain(tuple(run), state)


def offset_polyline(points: list[Point], distance: float) -> list[Point]:
    """The polyline moved sideways by distance (positive: to the right). Corners are joined by
    extending both offset segments. Raises TightCurveError when the line turns tighter than the
    distance, so an offset segment would run backwards."""

    points = [
        point for index, point in enumerate(points) if index == 0 or point != points[index - 1]
    ]

    if len(points) < 2:
        raise ParallelLaneError(tr("The chain has no length"))

    normals = []

    for (x0, z0), (x1, z1) in pairwise(points):
        length = math.dist((x0, z0), (x1, z1))
        normals.append((-(z1 - z0) / length, (x1 - x0) / length))

    offset = [_moved(points[0], normals[0], distance)]

    for index in range(1, len(points) - 1):
        before, after = normals[index - 1], normals[index]
        nx, nz = before[0] + after[0], before[1] + after[1]
        # Cosine of half the turn; zero for a U-turn.
        cosine = math.hypot(nx, nz) / 2

        if cosine < 1e-6:
            raise TightCurveError(index)

        offset.append(
            _moved(points[index], (nx / (2 * cosine), nz / (2 * cosine)), distance / cosine)
        )

    offset.append(_moved(points[-1], normals[-1], distance))

    for index, ((a, b), (c, d)) in enumerate(zip(pairwise(points), pairwise(offset), strict=True)):
        if (b[0] - a[0]) * (d[0] - c[0]) + (b[1] - a[1]) * (d[1] - c[1]) <= 0:
            raise TightCurveError(min(index + 1, len(points) - 2))

    return offset


def signed_distance(points: list[Point], x: float, z: float) -> float:
    """Distance of (x, z) from the polyline, positive when the point lies to its right."""

    best, best_side = math.inf, 1.0

    for (x0, z0), (x1, z1) in pairwise(points):
        _, distance = _closest_on_segment((x0, z0), (x1, z1), (x, z))

        if distance < best:
            # Right of the direction is where the normal (-dz, dx) points.
            side = (x - x0) * -(z1 - z0) + (z - z0) * (x1 - x0)
            best, best_side = distance, 1.0 if side >= 0 else -1.0

    return best * best_side


def parallel_lane(
    autodrive_data: AutoDriveData, chain: Chain, distance: float, spacing: float, opposite: bool
) -> list[tuple[float, float, float]]:
    """The nodes (x, y, z) of the lane beside the chain, evenly spaced, in the lane's driving
    order. The height is taken from the chain beside each node."""

    nodes = [autodrive_data.nodes[node_id] for node_id in chain.node_ids]
    points = [(node.x, node.z) for node in nodes]

    try:
        offset = offset_polyline(points, distance)
    except TightCurveError as error:
        raise ParallelLaneError(
            tr(
                "The road turns tighter than {distance} m at node {node}",
                distance=f"{abs(distance):g}",
                node=chain.node_ids[error.index],
            )
        ) from None

    lane = [(x, _height_beside(nodes, x, z), z) for x, z in spaced_points(offset, spacing)]

    return lane[::-1] if opposite else lane


def _height_beside(nodes, x: float, z: float) -> float:
    """Height of the chain at the point closest to (x, z)."""

    best, height = math.inf, nodes[0].y

    for a, b in pairwise(nodes):
        t, distance = _closest_on_segment((a.x, a.z), (b.x, b.z), (x, z))

        if distance < best:
            best, height = distance, a.y + t * (b.y - a.y)

    return height


def _closest_on_segment(a: Point, b: Point, point: Point) -> tuple[float, float]:
    """Fraction along a–b of the point closest to point, and the distance to it."""

    dx, dz = b[0] - a[0], b[1] - a[1]
    length_squared = dx * dx + dz * dz
    t = (
        0.0
        if length_squared == 0
        else ((point[0] - a[0]) * dx + (point[1] - a[1]) * dz) / length_squared
    )
    t = min(max(t, 0.0), 1.0)

    return t, math.dist(point, (a[0] + t * dx, a[1] + t * dz))


def _moved(point: Point, direction: Point, distance: float) -> Point:
    return point[0] + direction[0] * distance, point[1] + direction[1] * distance
