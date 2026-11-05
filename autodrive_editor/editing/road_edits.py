"""Edits of existing roads: splitting a connection with a new node."""

from autodrive_editor.editing.commands.add_route import AddRouteCommand
from autodrive_editor.i18n import tr
from autodrive_editor.model.autodrive_data import AutoDriveData, NodeData
from autodrive_editor.model.connections import NO_CONNECTION, read_connection_state


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
