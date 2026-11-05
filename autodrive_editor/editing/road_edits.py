"""Edits of existing roads: splitting a connection with a new node, deleting nodes and
reconnecting the road."""

from autodrive_editor.editing.commands.add_route import AddRouteCommand
from autodrive_editor.i18n import tr
from autodrive_editor.model.autodrive_data import AutoDriveData, NodeData
from autodrive_editor.model.connections import (
    NO_CONNECTION,
    ConnectionState,
    read_connection_state,
)


class ReconnectError(ValueError):
    """The nodes cannot be deleted with the road kept connected; the message says why."""


def split_connection(
    autodrive_data: AutoDriveData,
    source_id: int,
    target_id: int,
    x: float,
    z: float,
    node_id: int,
    flag: int,
) -> AddRouteCommand:
    """Command that puts a new node on the connection source–target at the point closest to
    (x, z). Both halves get the connection's entries, so type and direction stay; the height is
    taken between the two ends."""

    source = autodrive_data.nodes[source_id]
    target = autodrive_data.nodes[target_id]
    dx, dz = target.x - source.x, target.z - source.z
    length_squared = dx * dx + dz * dz
    t = 0.5 if length_squared == 0 else ((x - source.x) * dx + (z - source.z) * dz) / length_squared
    t = min(max(t, 0.0), 1.0)
    node = NodeData(
        node_id,
        source.x + t * dx,
        source.y + t * (target.y - source.y),
        source.z + t * dz,
        flag,
    )
    state = read_connection_state(autodrive_data, source_id, target_id)

    return AddRouteCommand(
        tr("Insert node"),
        autodrive_data,
        [node],
        [
            (source_id, target_id, NO_CONNECTION),
            (source_id, node_id, state),
            (node_id, target_id, state),
        ],
    )


def plan_reconnect(
    autodrive_data: AutoDriveData, node_ids
) -> list[tuple[int, int, ConnectionState]]:
    """The connections that keep the road connected when node_ids are deleted. Each run of
    deleted nodes must lie in the middle of a road (every node with exactly two neighbours) with
    the same connection type and direction all along; its two ends are then connected the same
    way. Raises ReconnectError otherwise."""

    nodes = autodrive_data.nodes
    node_ids = set(node_ids)
    # Reverse connections are only stored in the source node, so look for them in all nodes.
    neighbors = {node_id: nodes[node_id].incoming | nodes[node_id].outgoing for node_id in node_ids}

    for node in nodes.values():
        for target_id in node.outgoing & node_ids:
            neighbors[target_id].add(node.node_id)

    for node_id in sorted(node_ids):
        if len(neighbors[node_id] - {node_id}) != 2:
            raise ReconnectError(tr("Node {node} is a junction or a road end", node=node_id))

    connections = []
    done = set()

    for node_id in sorted(node_ids):
        if node_id in done:
            continue

        run = _run_through(node_id, node_ids, neighbors)
        done.update(run[1:-1])
        start, end = run[0], run[-1]
        states = {
            read_connection_state(autodrive_data, a, b) for a, b in zip(run, run[1:], strict=False)
        }

        if start == end:
            raise ReconnectError(tr("The nodes form a closed ring"))

        if len(states) > 1:
            raise ReconnectError(
                tr("The connections at node {node} differ in type or direction", node=node_id)
            )

        if read_connection_state(autodrive_data, start, end) != NO_CONNECTION or any(
            {start, end} == {a, b} for a, b, _ in connections
        ):
            raise ReconnectError(
                tr("Nodes {source} and {target} are already connected", source=start, target=end)
            )

        connections.append((start, end, states.pop()))

    return connections


def _run_through(node_id: int, node_ids: set[int], neighbors: dict[int, set[int]]) -> list[int]:
    """The run of deleted nodes through node_id with the kept node at each end, in road order."""

    halves = []

    for first in sorted(neighbors[node_id]):
        half, previous, current = [], node_id, first

        while current in node_ids and current != node_id:
            half.append(current)
            previous, current = current, next(iter(neighbors[current] - {previous}))

        if current == node_id:
            raise ReconnectError(tr("The nodes form a closed ring"))

        halves.append(half + [current])

    return halves[0][::-1] + [node_id] + halves[1]
