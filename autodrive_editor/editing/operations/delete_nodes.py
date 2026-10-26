from PySide6.QtCore import QPoint

from autodrive_editor.editing.commands.delete_nodes import DeleteNodesCommand
from autodrive_editor.editing.edit_context import EditContext, EditOperation
from autodrive_editor.i18n import tr


class DeleteNodesOperation(EditOperation):
    """Deletes nodes as one undoable step."""

    def __init__(self, context: EditContext, parent=None):
        super().__init__(context, parent)

    def delete_node_at(self, view_position: QPoint) -> bool:
        """Deletes the node at the view position, or the whole
        selection if that node is selected. Returns False if there is
        no node at the position."""

        clicked_node = self.selection_coordinator.get_node_at(view_position)

        if clicked_node is None:
            return False

        selected_node_ids = self.node_selection.selected_node_ids

        if clicked_node.node_id in selected_node_ids:
            return self.delete_nodes(selected_node_ids)

        return self.delete_nodes({clicked_node.node_id})

    def delete_selection(self) -> bool:
        return self.delete_nodes(self.node_selection.selected_node_ids)

    def delete_nodes(self, node_ids) -> bool:
        autodrive_data = self.autodrive_data_provider()

        if (
            autodrive_data is None
            or not node_ids
            # Never interleave with a running drag's undo steps.
            or self.edit_history.history_locked
        ):
            return False

        node_ids = {node_id for node_id in node_ids if node_id in autodrive_data.nodes}

        if not node_ids:
            return False

        self.edit_history.push(DeleteNodesCommand(autodrive_data, node_ids))

        self.status_changed.emit(
            tr("Node deleted")
            if len(node_ids) == 1
            else tr("{count} nodes deleted", count=len(node_ids))
        )

        return True
