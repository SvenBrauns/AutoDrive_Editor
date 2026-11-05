from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QMouseEvent

from autodrive_editor.editing.operations.delete_nodes import DeleteNodesOperation
from autodrive_editor.i18n import tr
from autodrive_editor.ui.tools.map_tool import MapTool


class DeleteNodesTool(MapTool):
    """Left click on a node deletes it, or the whole selection if the
    node is selected; with reconnect, the road around it stays
    connected. Left dragging pans the map."""

    def __init__(self, view, delete_nodes_operation: DeleteNodesOperation, reconnect=False):
        super().__init__(view)

        self.delete_nodes_operation = delete_nodes_operation
        self.reconnect = reconnect

    def mouse_release(self, event: QMouseEvent) -> bool:
        if event.button() != Qt.LeftButton:
            return False

        # Only a click deletes. Releasing after a pan does nothing.
        if not self._end_pan():
            self.delete_nodes_operation.delete_node_at(event.position().toPoint(), self.reconnect)

        return True

    def status_hint(self) -> str | None:
        if self.reconnect:
            return tr(
                "Click a node in the middle of a road to delete it and connect its neighbours;"
                " a selected node does this for the whole selection"
            )

        return tr("Click a node to delete it; a selected node deletes the whole selection")

    def cursor_at(self, view_position: QPoint) -> Qt.CursorShape:
        if self._pan.is_dragging:
            return Qt.ClosedHandCursor

        if self.view.has_node_at(view_position):
            return Qt.PointingHandCursor

        return Qt.OpenHandCursor
