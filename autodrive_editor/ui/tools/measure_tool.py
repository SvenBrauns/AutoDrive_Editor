from collections.abc import Callable

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QMouseEvent

from autodrive_editor.i18n import tr
from autodrive_editor.measurement.coordinator import MeasurementCoordinator
from autodrive_editor.measurement.mode import MeasurementMode
from autodrive_editor.ui.tools.interaction_mode import InteractionMode
from autodrive_editor.ui.tools.map_tool import DragGesture, MapTool

MODES = {
    InteractionMode.MEASURE_DISTANCE: MeasurementMode.DISTANCE,
    InteractionMode.MEASURE_ANGLE: MeasurementMode.ANGLE,
}


class MeasureTool(MapTool):
    """Left click sets measurement point A or B. Left dragging a free
    measurement point moves it. Left dragging empty map pans. Esc
    cancels a point drag, clears the measurement or calls finish (back to
    the tool before). One tool for distance and angle."""

    def __init__(
        self, view, measurement_coordinator: MeasurementCoordinator, finish: Callable[[], None]
    ):
        super().__init__(view)

        self.measurement_coordinator = measurement_coordinator
        self._finish = finish
        self._active = False

        self._point_drag = DragGesture()
        view.interaction_mode_changed.connect(self._change_mode)

    def activate(self):
        self._active = True
        self.measurement_coordinator.set_mode(MODES[self.view.interaction_mode])

    def _change_mode(self, mode: InteractionMode):
        """The view keeps this tool when only distance/angle changes."""

        if self._active and mode in MODES:
            self.measurement_coordinator.set_mode(MODES[mode])

    def status_hint(self) -> str | None:
        return tr("Click point A and point B (node or free ground); drag a point to move it")

    def mouse_press(self, event: QMouseEvent) -> bool:
        if event.button() != Qt.LeftButton:
            return False

        position = event.position().toPoint()

        self.measurement_coordinator.handle_press(position, event.modifiers())

        if self.measurement_coordinator.is_point_dragging:
            self._point_drag.press(Qt.LeftButton, position)

        else:
            self._begin_pan(event)

        return True

    def mouse_move(self, event: QMouseEvent) -> bool:
        position = event.position().toPoint()

        if self._point_drag.is_pressed:
            if self._point_drag.move(position) is not None:
                self.measurement_coordinator.handle_move(position, event.modifiers())

            return True

        if self._continue_pan(event):
            return True

        # Hovering shows the preview line to the second point.
        self.measurement_coordinator.handle_move(position, event.modifiers())

        return True

    def mouse_release(self, event: QMouseEvent) -> bool:
        if event.button() != Qt.LeftButton:
            return False

        position = event.position().toPoint()

        if self._point_drag.is_pressed:
            self._point_drag.reset()

            self.measurement_coordinator.handle_release(position, event.modifiers())

            return True

        # Releasing after panning the map is not a measurement click.
        if not self._end_pan():
            self.measurement_coordinator.handle_release(position, event.modifiers())

        return True

    def cancel(self) -> bool:
        self._point_drag.reset()
        self._pan.reset()

        if not self.measurement_coordinator.cancel():
            self._finish()

        return True

    def deactivate(self):
        # Not MapTool.deactivate: its cancel() could call finish.
        self._active = False
        self._point_drag.reset()
        self._pan.reset()
        self.measurement_coordinator.set_mode(MeasurementMode.INACTIVE)

    def cursor_at(self, view_position: QPoint) -> Qt.CursorShape:
        if self._point_drag.is_dragging:
            return Qt.SizeAllCursor

        if self._pan.is_dragging:
            return Qt.ClosedHandCursor

        return Qt.CrossCursor
