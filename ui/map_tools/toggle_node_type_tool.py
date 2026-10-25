from PySide6.QtCore import (
    QPoint,
    Qt
)
from PySide6.QtGui import QMouseEvent

from editing.node_flag_coordinator import (
    NodeFlagCoordinator
)
from ui.map_tools.map_tool import MapTool


class ToggleNodeTypeTool(MapTool):
    """Left click on a node switches it between regular and subprio,
    or the whole selection if the node is selected. Left dragging
    pans the map."""

    def __init__(
        self,
        view,
        node_flag_coordinator: NodeFlagCoordinator
    ):
        super().__init__(
            view
        )

        self.node_flag_coordinator = node_flag_coordinator

    def mouse_release(
        self,
        event: QMouseEvent
    ) -> bool:
        if event.button() != Qt.LeftButton:
            return False

        # Only a click switches. Releasing after a pan does nothing.
        if not self._end_pan():
            self.node_flag_coordinator.toggle_at(
                event.position().toPoint()
            )

        return True

    def status_hint(self) -> str | None:
        return (
            "Node anklicken, um zwischen Regular und Subprio "
            "zu wechseln"
        )

    def cursor_at(
        self,
        view_position: QPoint
    ) -> Qt.CursorShape:
        if self._pan.is_dragging:
            return Qt.ClosedHandCursor

        if self.view.has_selectable_item_at(
            view_position
        ):
            return Qt.PointingHandCursor

        return Qt.OpenHandCursor
