import math
from collections.abc import Callable
from typing import Protocol

from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QMouseEvent

from autodrive_editor.i18n import tr
from autodrive_editor.ui.tools.navigate_tool import NavigateTool

# (row, kind, x, z): the handle's row and kind as the dialog knows them, its map position.
Handle = tuple[int, object, float, float]

# How close to a handle a press grabs it, in pixels.
GRAB_PX = 10.0
# A handle moves only once the mouse is this far from where it was pressed, in pixels.
CLICK_PX = 3.0


class Drawing(Protocol):
    """Something the dialog draws on the map with clicks; each returns whether it was used."""

    def click(self, handle: Handle | None, x: float, z: float, node_id: int | None) -> bool:
        """A left click without dragging, on a handle or beside them."""

    def remove_last(self) -> bool:
        """Right-click."""

    def finish(self) -> bool:
        """Enter or Esc."""


class LaneHandleTool(NavigateTool):
    """For a dialog open beside the map: dragging a lane's handle passes the map position, the
    node under the mouse and whether Shift is held on to `drag`; left dragging elsewhere pans the
    map. Clicks, right-clicks, Enter and Esc go to `drawing`, if given."""

    # The right button goes to drawing.
    RIGHT_CLICK_CANCELS = False

    def __init__(
        self,
        view,
        handles: Callable[[], list[Handle]],
        drag: Callable[[Handle, float, float, int | None, bool], None],
        node_at: Callable[[QPoint], int | None],
        drawing: Drawing | None = None,
    ):
        super().__init__(view)

        self._handles = handles
        self._drag = drag
        self._node_at = node_at
        self._drawing = drawing
        self._dragged: Handle | None = None
        self._pressed_at = QPoint()
        self._moved = False

    def deactivate(self):
        super().deactivate()
        self._dragged = None

    def mouse_press(self, event: QMouseEvent) -> bool:
        if event.button() == Qt.LeftButton:
            self._pressed_at = event.position().toPoint()
            self._moved = False
            self._dragged = self._handle_at(self._pressed_at)

            if self._dragged is not None:
                return True

        if event.button() == Qt.RightButton and self._drawing is not None:
            return self._drawing.remove_last()

        return super().mouse_press(event)

    def mouse_move(self, event: QMouseEvent) -> bool:
        if self._dragged is None:
            return super().mouse_move(event)

        view_position = event.position().toPoint()
        offset = view_position - self._pressed_at

        if not self._moved and math.hypot(offset.x(), offset.y()) < CLICK_PX:
            return True

        self._moved = True
        position = self.view.mapToScene(view_position)
        snap = bool(event.modifiers() & Qt.ShiftModifier)
        self._drag(self._dragged, position.x(), position.y(), self._node_at(view_position), snap)

        return True

    def mouse_release(self, event: QMouseEvent) -> bool:
        if event.button() != Qt.LeftButton:
            return super().mouse_release(event)

        handle, self._dragged = self._dragged, None
        clicked = not self._moved if handle is not None else not self._end_pan()

        if clicked and self._drawing is not None:
            view_position = event.position().toPoint()
            position = self.view.mapToScene(view_position)
            self._drawing.click(handle, position.x(), position.y(), self._node_at(view_position))

        return True

    def cancel(self) -> bool:
        return self._drawing is not None and self._drawing.finish()

    def confirm(self) -> bool:
        return self._drawing is not None and self._drawing.finish()

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
