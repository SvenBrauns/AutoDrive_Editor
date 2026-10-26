from collections.abc import Callable

from PySide6.QtCore import QObject, QPoint, Signal

from autodrive_editor.editing.commands.move_nodes import MoveNodesCommand
from autodrive_editor.editing.edit_history import EditHistory
from autodrive_editor.i18n import tr
from autodrive_editor.model.autodrive_data import AutoDriveData, NodeData
from autodrive_editor.selection.selection_coordinator import SelectionCoordinator

# Asks for a node's new (x, y, z); None if cancelled.
PositionRequest = Callable[[NodeData], tuple[float, float, float] | None]


class NodePositionOperation(QObject):
    """Sets the exact position of a clicked node."""

    status_changed = Signal(str)

    def __init__(
        self,
        selection_coordinator: SelectionCoordinator,
        edit_history: EditHistory,
        autodrive_data_provider: Callable[[], AutoDriveData | None],
        ask_position: PositionRequest,
        parent=None,
    ):
        super().__init__(parent)

        self.selection_coordinator = selection_coordinator
        self.edit_history = edit_history
        self.autodrive_data_provider = autodrive_data_provider
        self.ask_position = ask_position

    def edit_at(self, view_position: QPoint) -> bool:
        autodrive_data = self.autodrive_data_provider()

        if autodrive_data is None or self.edit_history.history_locked:
            return False

        clicked_node = self.selection_coordinator.get_node_at(view_position)

        if clicked_node is None:
            return False

        node = autodrive_data.nodes[clicked_node.node_id]
        old_position = (node.x, node.y, node.z)
        new_position = self.ask_position(node)

        if new_position is None or tuple(new_position) == old_position:
            return False

        self.edit_history.push(
            MoveNodesCommand(
                autodrive_data,
                {node.node_id: old_position},
                {node.node_id: new_position},
                text=tr("Change node position"),
            )
        )

        self.status_changed.emit(tr("Position of node {node} changed", node=node.node_id))

        return True
