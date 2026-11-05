"""Whole road pieces: the nodes between two junctions or road ends."""

from autodrive_editor.model.autodrive_data import AutoDriveData
from autodrive_editor.model.connections import read_connection_state


def road_piece(autodrive_data: AutoDriveData, node_ids) -> set[int]:
    """The nodes of the road pieces through node_ids, ends included. From a junction, every
    piece that meets there."""

    neighbors = _neighbors(autodrive_data)
    piece = set(node_ids)

    for node_id in node_ids:
        for neighbor_id in neighbors[node_id]:
            piece |= _walk(autodrive_data, neighbors, node_id, neighbor_id)

    return piece


def connection_piece(autodrive_data: AutoDriveData, source_id: int, target_id: int) -> set[int]:
    """The nodes of the road piece the connection source–target lies on, ends included."""

    neighbors = _neighbors(autodrive_data)

    return (
        {source_id, target_id}
        | _walk(autodrive_data, neighbors, source_id, target_id)
        | _walk(autodrive_data, neighbors, target_id, source_id)
    )


def _neighbors(autodrive_data: AutoDriveData) -> dict[int, set[int]]:
    nodes = autodrive_data.nodes
    neighbors = {
        node_id: (node.incoming | node.outgoing) - {node_id} for node_id, node in nodes.items()
    }

    # Reverse connections are only stored in the source node.
    for node_id, node in nodes.items():
        for target_id in node.outgoing - {node_id}:
            neighbors[target_id].add(node_id)

    return neighbors


def _walk(autodrive_data, neighbors, start_id: int, first_id: int) -> set[int]:
    """The nodes from start_id over first_id on to the end of the piece: a junction, a road end,
    a change of connection type or direction (that node included) or a change of node type (that
    node left out)."""

    nodes = autodrive_data.nodes
    flag = nodes[start_id].flag
    walked, previous, current = set(), start_id, first_id

    while current not in walked and current != start_id and nodes[current].flag == flag:
        walked.add(current)

        if len(neighbors[current]) != 2:
            break

        following = next(iter(neighbors[current] - {previous}))
        state = read_connection_state(autodrive_data, previous, current)

        if read_connection_state(autodrive_data, current, following) != state:
            break

        previous, current = current, following

    return walked
