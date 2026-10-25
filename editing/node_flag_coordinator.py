from collections.abc import Callable

from PySide6.QtCore import QObject, QPoint, Signal

from autodrive.models import REGULAR_FLAG, SUBPRIO_FLAG, AutoDriveData
from editing.edit_coordinator import EditCoordinator
from editing.set_node_flags_command import SetNodeFlagsCommand
from selection.node_selection_manager import NodeSelectionManager
from selection.selection_coordinator import SelectionCoordinator


class NodeFlagCoordinator(QObject):
    """Switches nodes between regular and subprio."""

    status_changed = Signal(str)

    def __init__(
        self,
        selection_coordinator: SelectionCoordinator,
        selection_manager: NodeSelectionManager,
        edit_coordinator: EditCoordinator,
        autodrive_data_provider: Callable[[], AutoDriveData | None],
        parent=None,
    ):
        super().__init__(parent)

        self.selection_coordinator = selection_coordinator
        self.selection_manager = selection_manager
        self.edit_coordinator = edit_coordinator
        self.autodrive_data_provider = autodrive_data_provider

    def toggle_at(self, view_position: QPoint) -> bool:
        """Switches the node at the view position to the other type.
        If it is selected, the whole selection gets the opposite of
        the clicked node's type. Returns False if nothing changed."""

        autodrive_data = self.autodrive_data_provider()

        if autodrive_data is None or self.edit_coordinator.history_locked:
            return False

        node_item = self.selection_coordinator.get_node_item_at(view_position)

        if node_item is None:
            return False

        clicked_node = autodrive_data.get_node(node_item.node_id)

        new_flag = SUBPRIO_FLAG if clicked_node.is_regular else REGULAR_FLAG

        selected_node_ids = self.selection_manager.selected_node_ids

        if clicked_node.node_id in selected_node_ids:
            node_ids = {node_id for node_id in selected_node_ids if node_id in autodrive_data.nodes}

        else:
            node_ids = {clicked_node.node_id}

        changed_count = sum(
            1 for node_id in node_ids if autodrive_data.nodes[node_id].flag != new_flag
        )

        self.edit_coordinator.push(SetNodeFlagsCommand(autodrive_data, node_ids, new_flag))

        type_name = "Regular" if new_flag == REGULAR_FLAG else "Subprio"

        self.status_changed.emit(
            f"Node {clicked_node.node_id} auf {type_name} gesetzt"
            if len(node_ids) == 1
            else f"{changed_count} Nodes auf {type_name} gesetzt"
        )

        return True
