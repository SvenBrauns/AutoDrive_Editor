from PySide6.QtCore import (
    QPoint,
    Qt
)
from PySide6.QtGui import QMouseEvent

from editing.node_create_coordinator import (
    NodeCreateCoordinator
)
from ui.map_tools.map_tool import MapTool


class CreateNodeTool(MapTool):
    """Left click on empty map creates an unconnected node there.
    Clicking an existing node does nothing. Left dragging pans."""

    def __init__(
        self,
        view,
        node_create_coordinator: NodeCreateCoordinator
    ):
        super().__init__(
            view
        )

        self.node_create_coordinator = node_create_coordinator

    def mouse_release(
        self,
        event: QMouseEvent
    ) -> bool:
        if event.button() != Qt.LeftButton:
            return False

        # Only a click creates. Releasing after a pan does nothing.
        if not self._end_pan():
            self.node_create_coordinator.create_node_at(
                event.position().toPoint()
            )

        return True

    def cursor_at(
        self,
        view_position: QPoint
    ) -> Qt.CursorShape:
        if self._pan.is_dragging:
            return Qt.ClosedHandCursor

        if self.view.has_selectable_item_at(
            view_position
        ):
            return Qt.ArrowCursor

        return Qt.CrossCursor
