from collections.abc import Callable

from PySide6.QtCore import QObject, QPoint, Signal

from autodrive_editor.editing.commands.set_node_flags import SetNodeFlagsCommand
from autodrive_editor.editing.edit_history import EditHistory
from autodrive_editor.i18n import tr
from autodrive_editor.model.autodrive_data import REGULAR_FLAG, SUBPRIO_FLAG, AutoDriveData
from autodrive_editor.selection.node_selection import NodeSelection
from autodrive_editor.selection.selection_coordinator import SelectionCoordinator


class NodeTypeOperation(QObject):
    """Switches nodes between regular and subprio."""

    status_changed = Signal(str)

    def __init__(
        self,
        selection_coordinator: SelectionCoordinator,
        node_selection: NodeSelection,
        edit_history: EditHistory,
        autodrive_data_provider: Callable[[], AutoDriveData | None],
        parent=None,
    ):
        super().__init__(parent)

        self.selection_coordinator = selection_coordinator
        self.node_selection = node_selection
        self.edit_history = edit_history
        self.autodrive_data_provider = autodrive_data_provider

    def toggle_at(self, view_position: QPoint) -> bool:
        """Switches the node at the view position to the other type.
        If it is selected, the whole selection gets the opposite of
        the clicked node's type. Returns False if nothing changed."""

        autodrive_data = self.autodrive_data_provider()

        if autodrive_data is None or self.edit_history.history_locked:
            return False

        clicked_node = self.selection_coordinator.get_node_at(view_position)

        if clicked_node is None:
            return False

        # Nodes with flags other than regular/subprio keep their value.
        if not clicked_node.has_known_flag:
            self.status_changed.emit(
                tr(
                    "Node {node} has an unknown type (flag {flag}) and is not changed",
                    node=clicked_node.node_id,
                    flag=clicked_node.flag,
                )
            )
            return False

        new_flag = SUBPRIO_FLAG if clicked_node.is_regular else REGULAR_FLAG

        selected_node_ids = self.node_selection.selected_node_ids

        if clicked_node.node_id in selected_node_ids:
            node_ids = {
                node_id
                for node_id in selected_node_ids
                if node_id in autodrive_data.nodes and autodrive_data.nodes[node_id].has_known_flag
            }

        else:
            node_ids = {clicked_node.node_id}

        changed_count = sum(
            1 for node_id in node_ids if autodrive_data.nodes[node_id].flag != new_flag
        )

        self.edit_history.push(SetNodeFlagsCommand(autodrive_data, node_ids, new_flag))

        type_name = "Regular" if new_flag == REGULAR_FLAG else "Subprio"

        self.status_changed.emit(
            tr("Node {node} set to {type}", node=clicked_node.node_id, type=type_name)
            if len(node_ids) == 1
            else tr("{count} nodes set to {type}", count=changed_count, type=type_name)
        )

        return True
