import math
from collections.abc import Callable

from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QMouseEvent

from autodrive_editor.i18n import tr
from autodrive_editor.ui.tools.navigate_tool import NavigateTool

# (row, handle x, z, stop x, z) in map coordinates.
Handle = tuple[int, float, float, float, float]

# How close to a handle a press grabs it, in pixels.
GRAB_PX = 10.0
# Shift snaps the angle to multiples of this, in degrees.
SNAP_DEGREES = 15


class LaneHandleTool(NavigateTool):
    """For a dialog open beside the map: dragging a lane's handle turns the lane around its stop
    (Shift snaps to 15°); left dragging elsewhere pans the map."""

    def __init__(
        self, view, handles: Callable[[], list[Handle]], turn: Callable[[int, float], None]
    ):
        super().__init__(view)

        self._handles = handles
        self._turn = turn
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

        _, _, _, stop_x, stop_z = self._dragged
        position = self.view.mapToScene(event.position().toPoint())
        dx, dz = position.x() - stop_x, position.y() - stop_z

        if math.hypot(dx, dz) > 0:
            heading = math.degrees(math.atan2(dx, -dz)) % 360

            if event.modifiers() & Qt.ShiftModifier:
                heading = round(heading / SNAP_DEGREES) * SNAP_DEGREES

            self._turn(self._dragged[0], heading)

        return True

    def mouse_release(self, event: QMouseEvent) -> bool:
        if self._dragged is not None and event.button() == Qt.LeftButton:
            self._dragged = None
            return True

        return super().mouse_release(event)

    def status_hint(self) -> str | None:
        return tr("Drag the end of a lane to turn it around its stop (Shift: 15° steps)")

    def cursor_at(self, view_position: QPoint) -> Qt.CursorShape:
        if self._dragged is not None or self._handle_at(view_position) is not None:
            return Qt.SizeAllCursor

        return super().cursor_at(view_position)

    def _handle_at(self, view_position: QPoint) -> Handle | None:
        closest, closest_distance = None, GRAB_PX

        for handle in self._handles():
            point = self.view.mapFromScene(QPointF(handle[1], handle[2]))
            distance = math.hypot(point.x() - view_position.x(), point.y() - view_position.y())

            if distance <= closest_distance:
                closest, closest_distance = handle, distance

        return closest
