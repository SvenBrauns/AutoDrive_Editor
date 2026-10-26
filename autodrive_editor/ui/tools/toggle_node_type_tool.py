from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QMouseEvent

from autodrive_editor.editing.operations.node_types import NodeTypeOperation
from autodrive_editor.i18n import tr
from autodrive_editor.ui.tools.map_tool import MapTool


class ToggleNodeTypeTool(MapTool):
    """Left click on a node switches it between regular and subprio,
    or the whole selection if the node is selected. Left dragging
    pans the map."""

    def __init__(self, view, node_type_operation: NodeTypeOperation):
        super().__init__(view)

        self.node_type_operation = node_type_operation

    def mouse_release(self, event: QMouseEvent) -> bool:
        if event.button() != Qt.LeftButton:
            return False

        # Only a click switches. Releasing after a pan does nothing.
        if not self._end_pan():
            self.node_type_operation.toggle_at(event.position().toPoint())

        return True

    def status_hint(self) -> str | None:
        return tr("Click a node to switch between regular and subprio")

    def cursor_at(self, view_position: QPoint) -> Qt.CursorShape:
        if self._pan.is_dragging:
            return Qt.ClosedHandCursor

        if self.view.has_node_at(view_position):
            return Qt.PointingHandCursor

        return Qt.OpenHandCursor
