from PySide6.QtCore import QPoint, QRectF, Qt, Signal
from PySide6.QtGui import QCursor, QKeyEvent, QMouseEvent, QResizeEvent, QWheelEvent
from PySide6.QtWidgets import QGraphicsItem, QGraphicsView

from autodrive_editor.ui.map_view.rotation_controller import ViewRotationController
from autodrive_editor.ui.map_view.zoom_controller import ViewZoomController
from autodrive_editor.ui.tools.interaction_mode import InteractionMode
from autodrive_editor.ui.tools.map_tool import DragGesture, MapTool
from autodrive_editor.ui.tools.navigate_tool import NavigateTool


class MapView(QGraphicsView):
    """The map. Zooming with the wheel and rotating with the middle
    button work for every tool. Everything else is forwarded to the
    active MapTool."""

    zoom_changed = Signal(float)

    rotation_changed = Signal(float)

    rotation_step_changed = Signal(float)

    visible_scene_rect_changed = Signal(QRectF)

    interaction_mode_changed = Signal(object)

    def __init__(self):
        super().__init__()

        self._interaction_mode = InteractionMode.NAVIGATE

        self._tools: dict[InteractionMode, MapTool] = {InteractionMode.NAVIGATE: NavigateTool(self)}

        # While measuring, the measure tool replaces the tool of the
        # current interaction mode.
        self._measure_tool: MapTool | None = None
        self._measurement_active = False

        self._rotation_drag = DragGesture()

        self._configure_view()

        self._zoom_controller = ViewZoomController(view=self, parent=self)

        self._zoom_controller.zoom_changed.connect(self.zoom_changed.emit)

        self._zoom_controller.visible_scene_rect_changed.connect(
            self.visible_scene_rect_changed.emit
        )

        self._rotation_controller = ViewRotationController(
            view=self,
            viewport_update_callback=self._zoom_controller.schedule_viewport_update,
            parent=self,
        )

        self._rotation_controller.rotation_changed.connect(self.rotation_changed.emit)

        self._rotation_controller.rotation_step_changed.connect(self.rotation_step_changed.emit)

        self.refresh_cursor()

    @property
    def zoom_level(self) -> float:
        return self._zoom_controller.zoom_level

    @property
    def rotation_angle(self) -> float:
        return self._rotation_controller.rotation_angle

    @property
    def rotation_step(self) -> float:
        return self._rotation_controller.rotation_step

    @property
    def interaction_mode(self) -> InteractionMode:
        return self._interaction_mode

    @property
    def measurement_active(self) -> bool:
        return self._measurement_active

    @property
    def active_tool(self) -> MapTool:
        if self._measurement_active and self._measure_tool is not None:
            return self._measure_tool

        return self._tools[self._interaction_mode]

    def register_tool(self, interaction_mode: InteractionMode, tool: MapTool):
        if not isinstance(tool, MapTool):
            raise TypeError("Invalid tool.")

        if interaction_mode == self._interaction_mode:
            self.active_tool.deactivate()

        self._tools[interaction_mode] = tool

        if interaction_mode == self._interaction_mode:
            tool.activate()

    def register_measure_tool(self, tool: MapTool):
        if not isinstance(tool, MapTool):
            raise TypeError("Invalid measuring tool.")

        self._measure_tool = tool

    def set_zoom_level(self, zoom_level):
        self._zoom_controller.set_zoom_level(zoom_level)

    def set_rotation_angle(self, rotation_angle: float):
        self._rotation_controller.set_rotation_angle(rotation_angle)

    def set_exact_rotation_angle(self, rotation_angle: float):
        self._rotation_controller.set_exact_rotation_angle(rotation_angle)

    def set_rotation_step(self, rotation_step: float):
        self._rotation_controller.set_rotation_step(rotation_step)

    def reset_view_rotation(self):
        self._rotation_controller.reset_rotation()

    def set_interaction_mode(self, interaction_mode: InteractionMode):
        if not isinstance(interaction_mode, InteractionMode):
            raise TypeError("Invalid interaction mode.")

        if interaction_mode == self._interaction_mode:
            return

        if interaction_mode not in self._tools:
            raise ValueError(f"No tool is registered for the mode {interaction_mode.name}.")

        self._switch_tool(lambda: setattr(self, "_interaction_mode", interaction_mode))

        self.interaction_mode_changed.emit(interaction_mode)

    def set_measurement_active(self, active: bool):
        active = bool(active)

        if active == self._measurement_active:
            return

        self._switch_tool(lambda: setattr(self, "_measurement_active", active))

    def get_visible_scene_rect(self) -> QRectF:
        return self._zoom_controller.get_visible_scene_rect()

    def pan_by(self, movement: QPoint):
        """Moves the visible map area with the mouse movement."""

        self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - movement.x())

        self.verticalScrollBar().setValue(self.verticalScrollBar().value() - movement.y())

    def has_selectable_item_at(self, view_position: QPoint) -> bool:
        for item in self.items(view_position):
            if item.flags() & QGraphicsItem.ItemIsSelectable:
                return True

        return False

    def refresh_cursor(self, view_position: QPoint | None = None):
        if view_position is None:
            view_position = self.viewport().mapFromGlobal(QCursor.pos())

        if self._rotation_drag.is_pressed:
            cursor_shape = Qt.SizeAllCursor

        else:
            cursor_shape = self.active_tool.cursor_at(view_position)

        self.viewport().setCursor(cursor_shape)

    def fitInView(self, *args):
        super().fitInView(*args)

        self._zoom_controller.notify_transform_changed()

    def wheelEvent(self, event: QWheelEvent):
        zoom_handled = self._zoom_controller.zoom_by_wheel_delta(
            wheel_delta=(event.angleDelta().y()), view_position=(event.position().toPoint())
        )

        if zoom_handled:
            event.accept()

        else:
            event.ignore()

    def resizeEvent(self, event: QResizeEvent):
        super().resizeEvent(event)

        self._zoom_controller.schedule_viewport_update()

    def mousePressEvent(self, event: QMouseEvent):
        mouse_position = event.position().toPoint()

        if event.button() == Qt.MiddleButton:
            self._rotation_drag.press(Qt.MiddleButton, mouse_position)

            handled = True

        elif event.button() == Qt.RightButton and self.active_tool.RIGHT_CLICK_CANCELS:
            # Same as Esc: cancels the running step of the tool.
            self.active_tool.cancel()

            handled = True

        else:
            handled = self.active_tool.mouse_press(event)

        if not handled:
            super().mousePressEvent(event)
            return

        self.refresh_cursor(mouse_position)

        event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        mouse_position = event.position().toPoint()

        if self._rotation_drag.is_pressed and event.buttons() & Qt.MiddleButton:
            movement = self._rotation_drag.move(mouse_position)

            if movement is not None:
                self._rotation_controller.rotate_by_horizontal_pixels(movement.x())

            handled = True

        else:
            handled = self.active_tool.mouse_move(event)

        self.refresh_cursor(mouse_position)

        if handled:
            event.accept()

        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        mouse_position = event.position().toPoint()

        if event.button() == Qt.MiddleButton and self._rotation_drag.is_pressed:
            self._rotation_drag.reset()

            handled = True

        else:
            handled = self.active_tool.mouse_release(event)

        self.refresh_cursor(mouse_position)

        if handled:
            event.accept()

        else:
            super().mouseReleaseEvent(event)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Escape and self.active_tool.cancel():
            self.refresh_cursor()

            event.accept()
            return

        if event.key() in (Qt.Key_Return, Qt.Key_Enter) and self.active_tool.confirm():
            self.refresh_cursor()

            event.accept()
            return

        super().keyPressEvent(event)

    def _switch_tool(self, change_state):
        """Deactivates the current tool, applies the state change and
        activates the tool that is active afterwards."""

        previous_tool = self.active_tool

        change_state()

        next_tool = self.active_tool

        if next_tool is not previous_tool:
            previous_tool.deactivate()
            next_tool.activate()

        self.refresh_cursor()

    def _configure_view(self):
        self.setMouseTracking(True)

        self.viewport().setMouseTracking(True)

        self.setInteractive(False)

        self.setDragMode(QGraphicsView.NoDrag)

        self.setTransformationAnchor(QGraphicsView.NoAnchor)

        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)
