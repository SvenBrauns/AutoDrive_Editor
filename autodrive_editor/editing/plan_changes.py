from autodrive_editor.editing.commands.edit_command import DataChange
from autodrive_editor.model.autodrive_data import AutoDriveData


def node_state(autodrive_data: AutoDriveData, node_id: int) -> tuple | None:
    """Everything an edit can change about a node, or None if it does not exist."""

    node = autodrive_data.nodes.get(node_id)

    if node is None:
        return None

    marker = autodrive_data.markers.get(node_id)

    return (
        node.x,
        node.y,
        node.z,
        node.flag,
        frozenset(node.incoming),
        frozenset(node.outgoing),
        None if marker is None else (marker.name, marker.group),
    )


class PlanChanges:
    """The nodes a plan changed. Keeps the state of every node at the start of the plan and
    finds the nodes that differ from it now, so an edit undone inside the plan no longer
    counts."""

    def __init__(self, autodrive_data: AutoDriveData):
        self.autodrive_data = autodrive_data

        self._original = {
            node_id: node_state(autodrive_data, node_id) for node_id in autodrive_data.nodes
        }

        self.changed_node_ids: set[int] = set()

    def update(self, data_change: DataChange):
        node_ids = (
            data_change.moved_node_ids
            | data_change.added_node_ids
            | data_change.removed_node_ids
            | data_change.connection_node_ids
            | data_change.changed_flag_node_ids
            | data_change.changed_marker_node_ids
        )

        for node_id in node_ids:
            state = node_state(self.autodrive_data, node_id)

            # Removed nodes cannot be drawn, so they are not highlighted.
            if state is not None and state != self._original.get(node_id):
                self.changed_node_ids.add(node_id)
            else:
                self.changed_node_ids.discard(node_id)
