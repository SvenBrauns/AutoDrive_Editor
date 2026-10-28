"""Connection types and how they are stored in the node data.

AutoDrive stores connections as sets of node ids on both ends:
`outgoing` on the source node and `incoming` on the target node. The
combination of these entries for a node pair decides the type.
"""

from enum import StrEnum

from autodrive_editor.model.autodrive_data import AutoDriveData, NodeData


class ConnectionType(StrEnum):
    """The three kinds of AutoDrive connections."""

    REGULAR = "regular"
    DUAL = "dual"
    REVERSE = "reverse"


def get_connection_type(source_node: NodeData, target_node: NodeData) -> ConnectionType:
    """Type of the connection from source_node to target_node. The
    caller must make sure that target_node is in source_node.outgoing."""

    if is_dual_connection(source_node, target_node):
        return ConnectionType.DUAL

    if is_reverse_connection(source_node, target_node):
        return ConnectionType.REVERSE

    return ConnectionType.REGULAR


def is_dual_connection(source_node: NodeData, target_node: NodeData) -> bool:
    """Both nodes list each other as incoming and outgoing."""

    return (
        target_node.node_id in source_node.outgoing
        and target_node.node_id in source_node.incoming
        and source_node.node_id in target_node.outgoing
        and source_node.node_id in target_node.incoming
    )


def is_reverse_connection(source_node: NodeData, target_node: NodeData) -> bool:
    """The source lists the target as outgoing, but the target does not
    list the source as incoming. Vehicles drive this one backwards."""

    return (
        target_node.node_id in source_node.outgoing
        and source_node.node_id not in target_node.incoming
    )


# The four entries that can exist between source A and target B:
# (A.outgoing has B, A.incoming has B, B.outgoing has A, B.incoming has A)
ConnectionState = tuple[bool, bool, bool, bool]

NO_CONNECTION: ConnectionState = (False, False, False, False)

# The entries each connection type sets for a connection from A to B.
CONNECTION_STATES: dict[ConnectionType, ConnectionState] = {
    ConnectionType.REGULAR: (True, False, False, True),
    ConnectionType.DUAL: (True, True, True, True),
    ConnectionType.REVERSE: (True, False, False, False),
}


def read_connection_state(
    autodrive_data: AutoDriveData, source_id: int, target_id: int
) -> ConnectionState:
    source = autodrive_data.nodes[source_id]
    target = autodrive_data.nodes[target_id]

    return (
        target_id in source.outgoing,
        target_id in source.incoming,
        source_id in target.outgoing,
        source_id in target.incoming,
    )


def write_connection_state(
    autodrive_data: AutoDriveData, source_id: int, target_id: int, state: ConnectionState
) -> None:
    source = autodrive_data.nodes[source_id]
    target = autodrive_data.nodes[target_id]

    entries = (
        (source.outgoing, target_id),
        (source.incoming, target_id),
        (target.outgoing, source_id),
        (target.incoming, source_id),
    )

    for (connections, node_id), present in zip(entries, state, strict=True):
        if present:
            connections.add(node_id)

        else:
            connections.discard(node_id)
