import math
from collections.abc import Callable

from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QMouseEvent

from autodrive_editor.i18n import tr
from autodrive_editor.ui.tools.navigate_tool import NavigateTool

# (row, kind, x, z): the handle's row and kind as the dialog knows them, its map position.
Handle = tuple[int, object, float, float]

# How close to a handle a press grabs it, in pixels.
GRAB_PX = 10.0


class LaneHandleTool(NavigateTool):
    """For a dialog open beside the map: dragging a lane's handle passes the map position, the
    node under the mouse and whether Shift is held on to `drag`; left dragging elsewhere pans the
    map."""

    def __init__(
        self,
        view,
        handles: Callable[[], list[Handle]],
        drag: Callable[[Handle, float, float, int | None, bool], None],
        node_at: Callable[[QPoint], int | None],
    ):
        super().__init__(view)

        self._handles = handles
        self._drag = drag
        self._node_at = node_at
        self._dragged: Handle | None = None

    def deactivate(self):
        super().deactivate()
        self._dragged = None

    def mouse_press(self, event: QMouseEvent) -> bool:
        if event.button() == Qt.LeftButton:
            self._dragged = self._handle_at(event.position().toPoint())

            if self._dragged is not None:
                return True

        return super().mouse_press(event)

    def mouse_move(self, event: QMouseEvent) -> bool:
        if self._dragged is None:
            return super().mouse_move(event)

        view_position = event.position().toPoint()
        position = self.view.mapToScene(view_position)
        snap = bool(event.modifiers() & Qt.ShiftModifier)
        self._drag(self._dragged, position.x(), position.y(), self._node_at(view_position), snap)

        return True

    def mouse_release(self, event: QMouseEvent) -> bool:
        if self._dragged is not None and event.button() == Qt.LeftButton:
            self._dragged = None
            return True

        return super().mouse_release(event)

    def status_hint(self) -> str | None:
        return tr(
            "Drag the marker of a lane to turn it (Shift: 15° steps), its ends to bend it; drop an "
            "end on a node to join it"
        )

    def cursor_at(self, view_position: QPoint) -> Qt.CursorShape:
        if self._dragged is not None or self._handle_at(view_position) is not None:
            return Qt.SizeAllCursor

        return super().cursor_at(view_position)

    def _handle_at(self, view_position: QPoint) -> Handle | None:
        closest, closest_distance = None, GRAB_PX

        for handle in self._handles():
            point = self.view.mapFromScene(QPointF(handle[2], handle[3]))
            distance = math.hypot(point.x() - view_position.x(), point.y() - view_position.y())

            if distance <= closest_distance:
                closest, closest_distance = handle, distance

        return closest
