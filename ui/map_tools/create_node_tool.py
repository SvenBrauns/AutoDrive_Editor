from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QMouseEvent

from autodrive.models import REGULAR_FLAG
from editing.node_create_coordinator import NodeCreateCoordinator
from ui.map_tools.map_tool import MapTool


class CreateNodeTool(MapTool):
    """Left click on empty map creates an unconnected node with the
    tool's flag (regular or subprio). Clicking an existing node does
    nothing. Left dragging pans."""

    def __init__(self, view, node_create_coordinator: NodeCreateCoordinator, flag: int):
        super().__init__(view)

        self.node_create_coordinator = node_create_coordinator
        self.flag = flag

    def mouse_release(self, event: QMouseEvent) -> bool:
        if event.button() != Qt.LeftButton:
            return False

        # Only a click creates. Releasing after a pan does nothing.
        if not self._end_pan():
            self.node_create_coordinator.create_node_at(event.position().toPoint(), self.flag)

        return True

    def status_hint(self) -> str | None:
        node_type = "Regular" if self.flag == REGULAR_FLAG else "Subprio"

        return f"Auf freie Fläche klicken, um eine {node_type}-Node zu erstellen"

    def cursor_at(self, view_position: QPoint) -> Qt.CursorShape:
        if self._pan.is_dragging:
            return Qt.ClosedHandCursor

        if self.view.has_selectable_item_at(view_position):
            return Qt.ArrowCursor

        return Qt.CrossCursor
