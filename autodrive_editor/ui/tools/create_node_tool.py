from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QMouseEvent

from autodrive_editor.editing.operations.create_nodes import CreateNodesOperation
from autodrive_editor.i18n import tr
from autodrive_editor.model.autodrive_data import REGULAR_FLAG
from autodrive_editor.ui.tools.map_tool import MapTool


class CreateNodeTool(MapTool):
    """Left click on empty map creates an unconnected node with the
    tool's flag (regular or subprio). Clicking an existing node does
    nothing. Left dragging pans."""

    def __init__(self, view, create_nodes_operation: CreateNodesOperation, flag: int):
        super().__init__(view)

        self.create_nodes_operation = create_nodes_operation
        self.flag = flag

    def mouse_release(self, event: QMouseEvent) -> bool:
        if event.button() != Qt.LeftButton:
            return False

        # Only a click creates. Releasing after a pan does nothing.
        if not self._end_pan():
            self.create_nodes_operation.create_node_at(event.position().toPoint(), self.flag)

        return True

    def status_hint(self) -> str | None:
        node_type = "Regular" if self.flag == REGULAR_FLAG else "Subprio"

        return tr("Click on free ground to create a {type} node", type=node_type)

    def cursor_at(self, view_position: QPoint) -> Qt.CursorShape:
        if self._pan.is_dragging:
            return Qt.ClosedHandCursor

        if self.view.has_node_at(view_position):
            return Qt.ArrowCursor

        return Qt.CrossCursor
