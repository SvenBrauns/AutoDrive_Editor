from collections.abc import Callable

from PySide6.QtCore import QObject, QPoint, Signal

from autodrive_editor.editing.commands.delete_nodes import DeleteNodesCommand
from autodrive_editor.editing.edit_history import EditCoordinator
from autodrive_editor.model.autodrive_data import AutoDriveData
from autodrive_editor.selection.node_selection import NodeSelectionManager
from autodrive_editor.selection.selection_coordinator import SelectionCoordinator


class NodeDeleteCoordinator(QObject):
    """Deletes nodes as one undoable step."""

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

    def delete_node_at(self, view_position: QPoint) -> bool:
        """Deletes the node at the view position, or the whole
        selection if that node is selected. Returns False if there is
        no node at the position."""

        node_item = self.selection_coordinator.get_node_item_at(view_position)

        if node_item is None:
            return False

        selected_node_ids = self.selection_manager.selected_node_ids

        if node_item.node_id in selected_node_ids:
            return self.delete_nodes(selected_node_ids)

        return self.delete_nodes({node_item.node_id})

    def delete_selection(self) -> bool:
        return self.delete_nodes(self.selection_manager.selected_node_ids)

    def delete_nodes(self, node_ids) -> bool:
        autodrive_data = self.autodrive_data_provider()

        if (
            autodrive_data is None
            or not node_ids
            # Never interleave with a running drag's undo steps.
            or self.edit_coordinator.history_locked
        ):
            return False

        node_ids = {node_id for node_id in node_ids if node_id in autodrive_data.nodes}

        if not node_ids:
            return False

        self.edit_coordinator.push(DeleteNodesCommand(autodrive_data, node_ids))

        self.status_changed.emit(
            "Node gelöscht" if len(node_ids) == 1 else f"{len(node_ids)} Nodes gelöscht"
        )

        return True
