from PySide6.QtCore import (
    QPoint,
    Qt
)
from PySide6.QtGui import QMouseEvent

from editing.node_drag_coordinator import (
    NodeDragCoordinator
)
from ui.map_tools.map_tool import (
    DragGesture,
    MapTool
)


class MoveNodesTool(MapTool):
    """Left dragging a node moves it, or the whole selection if the
    node is selected. Left dragging empty map pans. Esc cancels."""

    def __init__(
        self,
        view,
        node_drag_coordinator: NodeDragCoordinator
    ):
        super().__init__(
            view
        )

        self.node_drag_coordinator = node_drag_coordinator

        self._node_drag = DragGesture()

    def mouse_press(
        self,
        event: QMouseEvent
    ) -> bool:
        if event.button() != Qt.LeftButton:
            return False

        position = event.position().toPoint()

        if self.node_drag_coordinator.begin_drag(
            position
        ):
            self._node_drag.press(
                Qt.LeftButton,
                position
            )

            return True

        return super().mouse_press(
            event
        )

    def mouse_move(
        self,
        event: QMouseEvent
    ) -> bool:
        if not self._node_drag.is_pressed:
            return super().mouse_move(
                event
            )

        position = event.position().toPoint()

        # Nodes only move once the drag threshold is reached.
        if self._node_drag.move(position) is not None:
            self.node_drag_coordinator.update_drag(
                position
            )

        return True

    def mouse_release(
        self,
        event: QMouseEvent
    ) -> bool:
        if (
            event.button() == Qt.LeftButton
            and self._node_drag.is_pressed
        ):
            self._node_drag.reset()

            self.node_drag_coordinator.finish_drag()

            return True

        return super().mouse_release(
            event
        )

    def cancel(self) -> bool:
        if not self._node_drag.is_pressed:
            return False

        self._node_drag.reset()

        self.node_drag_coordinator.cancel_drag()

        return True

    def cursor_at(
        self,
        view_position: QPoint
    ) -> Qt.CursorShape:
        if self._node_drag.is_dragging:
            return Qt.SizeAllCursor

        if self._pan.is_dragging:
            return Qt.ClosedHandCursor

        if self.view.has_selectable_item_at(
            view_position
        ):
            return Qt.SizeAllCursor

        return Qt.OpenHandCursor
