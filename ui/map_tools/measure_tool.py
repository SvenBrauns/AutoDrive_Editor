from PySide6.QtCore import (
    QPoint,
    Qt
)
from PySide6.QtGui import QMouseEvent

from measurement.measurement_coordinator import (
    MeasurementCoordinator
)
from ui.map_tools.map_tool import (
    DragGesture,
    MapTool
)


class MeasureTool(MapTool):
    """Left click sets measurement point A or B. Left dragging a free
    measurement point moves it. Left dragging empty map pans. Esc
    cancels a point drag, clears the measurement or ends measuring."""

    def __init__(
        self,
        view,
        measurement_coordinator: MeasurementCoordinator
    ):
        super().__init__(
            view
        )

        self.measurement_coordinator = measurement_coordinator

        self._point_drag = DragGesture()

    def mouse_press(
        self,
        event: QMouseEvent
    ) -> bool:
        if event.button() != Qt.LeftButton:
            return False

        position = event.position().toPoint()

        self.measurement_coordinator.handle_press(
            position,
            event.modifiers()
        )

        if self.measurement_coordinator.is_point_dragging:
            self._point_drag.press(
                Qt.LeftButton,
                position
            )

        else:
            self._begin_pan(
                event
            )

        return True

    def mouse_move(
        self,
        event: QMouseEvent
    ) -> bool:
        position = event.position().toPoint()

        if self._point_drag.is_pressed:
            if self._point_drag.move(position) is not None:
                self.measurement_coordinator.handle_move(
                    position,
                    event.modifiers()
                )

            return True

        if self._continue_pan(event):
            return True

        # Hovering shows the preview line to the second point.
        self.measurement_coordinator.handle_move(
            position,
            event.modifiers()
        )

        return True

    def mouse_release(
        self,
        event: QMouseEvent
    ) -> bool:
        if event.button() != Qt.LeftButton:
            return False

        position = event.position().toPoint()

        if self._point_drag.is_pressed:
            self._point_drag.reset()

            self.measurement_coordinator.handle_release(
                position,
                event.modifiers()
            )

            return True

        # Releasing after panning the map is not a measurement click.
        if not self._end_pan():
            self.measurement_coordinator.handle_release(
                position,
                event.modifiers()
            )

        return True

    def cancel(self) -> bool:
        self._point_drag.reset()
        self._pan.reset()

        self.measurement_coordinator.cancel()

        return True

    def deactivate(self):
        # Ending measuring is done by the coordinator itself, so only
        # forget the gestures here instead of calling cancel().
        self._point_drag.reset()
        self._pan.reset()

    def cursor_at(
        self,
        view_position: QPoint
    ) -> Qt.CursorShape:
        if self._point_drag.is_dragging:
            return Qt.SizeAllCursor

        if self._pan.is_dragging:
            return Qt.ClosedHandCursor

        return Qt.CrossCursor
