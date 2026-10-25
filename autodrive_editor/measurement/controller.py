from PySide6.QtCore import QObject, QPointF, Signal
from PySide6.QtWidgets import QGraphicsScene

from autodrive_editor.measurement.mode import MeasurementMode
from autodrive_editor.measurement.point import MeasurementPoint
from autodrive_editor.measurement.point_drag_controller import PointDragController
from autodrive_editor.measurement.state import MeasurementState
from autodrive_editor.rendering.items.measurement_handle_item import MeasurementHandleItem
from autodrive_editor.rendering.items.measurement_line_item import MeasurementLineItem
from autodrive_editor.rendering.items.measurement_result_item import MeasurementResultItem


class MeasurementController(QObject):
    mode_changed = Signal(object)

    measurement_changed = Signal(object)

    measurement_cleared = Signal()

    def __init__(self, scene: QGraphicsScene, parent=None):
        super().__init__(parent)

        self.scene = scene

        self.state = MeasurementState()

        self.drag_controller = PointDragController(self)

        self.start_handle = None
        self.end_handle = None
        self.line_item = None
        self.result_item = None

        self._create_scene_items()
        self._connect_drag_controller()

    @property
    def mode(self) -> MeasurementMode:
        return self.state.mode

    @property
    def is_active(self) -> bool:
        return self.state.is_active

    @property
    def is_complete(self) -> bool:
        return self.state.is_complete

    @property
    def is_dragging(self) -> bool:
        return self.drag_controller.is_active

    def activate(self, measurement_mode: MeasurementMode):
        if not isinstance(measurement_mode, MeasurementMode):
            raise TypeError("Der Messmodus ist ungültig.")

        if measurement_mode == MeasurementMode.INACTIVE:
            self.deactivate()
            return

        self.cancel_drag()

        self.state.activate(measurement_mode)

        self._ensure_scene_items()
        self._clear_scene_items()

        self.mode_changed.emit(measurement_mode)

    def deactivate(self):
        self.cancel_drag()

        self.state.deactivate()

        self._clear_scene_items()

        self.mode_changed.emit(MeasurementMode.INACTIVE)

        self.measurement_cleared.emit()

    def clear_measurement(self):
        self.cancel_drag()

        self.state.clear_points()

        self._clear_scene_items()

        self.measurement_cleared.emit()

    def set_start_point(self, measurement_point: MeasurementPoint):
        self._validate_active_mode()

        self._ensure_scene_items()

        self.state.set_start_point(measurement_point)

        self._update_scene_items()

    def set_end_point(self, measurement_point: MeasurementPoint):
        self._validate_active_mode()

        self._ensure_scene_items()

        self.state.set_end_point(measurement_point)

        self._update_scene_items()

    def set_preview_position(self, scene_position: QPointF | None):
        if not self.is_active:
            return

        self._ensure_scene_items()

        self.state.set_preview_position(scene_position)

        self._update_scene_items(include_preview=True)

    def begin_point_drag(self, point_index: int, press_scene_position: QPointF) -> bool:
        if not self.is_active:
            return False

        measurement_point = self.state.get_point(point_index)

        if measurement_point is None:
            return False

        if not measurement_point.is_free_point:
            return False

        self.drag_controller.begin_drag(
            point_index=point_index,
            press_scene_position=press_scene_position,
            original_point_position=measurement_point.position,
        )

        return True

    def update_point_drag(self, scene_position: QPointF):
        if not self.is_dragging:
            return

        self.drag_controller.update_drag(scene_position)

    def finish_point_drag(self):
        if not self.is_dragging:
            return

        self.drag_controller.finish_drag()

        self._update_scene_items()

    def cancel_drag(self):
        if not self.is_dragging:
            return

        self.drag_controller.cancel_drag()

        self._update_scene_items()

    def get_handle_at_scene_position(
        self, scene_position: QPointF, scene_tolerance: float
    ) -> int | None:
        if not self.is_active:
            return None

        scene_tolerance = max(0.0, float(scene_tolerance))

        start_point = self.state.start_point

        if (
            start_point is not None
            and start_point.is_free_point
            and self._is_position_near_point(scene_position, start_point.position, scene_tolerance)
        ):
            return 0

        end_point = self.state.end_point

        if (
            end_point is not None
            and end_point.is_free_point
            and self._is_position_near_point(scene_position, end_point.position, scene_tolerance)
        ):
            return 1

        return None

    def restore_scene_items(self):
        if not self.is_active:
            return

        self._ensure_scene_items()
        self._update_scene_items()

    def remove_scene_items(self):
        self.cancel_drag()

        self._remove_item_from_scene(self.start_handle)

        self._remove_item_from_scene(self.end_handle)

        self._remove_item_from_scene(self.line_item)

        self._remove_item_from_scene(self.result_item)

        self.start_handle = None
        self.end_handle = None
        self.line_item = None
        self.result_item = None

    def _create_scene_items(self):
        self.start_handle = MeasurementHandleItem(point_index=0, label="A", movable=True)

        self.end_handle = MeasurementHandleItem(point_index=1, label="B", movable=True)

        self.line_item = MeasurementLineItem()

        self.result_item = MeasurementResultItem()

        self.scene.addItem(self.line_item)

        self.scene.addItem(self.start_handle)

        self.scene.addItem(self.end_handle)

        self.scene.addItem(self.result_item)

        self._clear_scene_items()

    def _ensure_scene_items(self):
        if self.start_handle is None:
            self._create_scene_items()
            return

        scene_items = (self.start_handle, self.end_handle, self.line_item, self.result_item)

        if any(item.scene() is not self.scene for item in scene_items):
            self.remove_scene_items()
            self._create_scene_items()

    def _connect_drag_controller(self):
        self.drag_controller.position_requested.connect(self._handle_drag_position_requested)

        self.drag_controller.drag_cancelled.connect(self._handle_drag_cancelled)

    def _handle_drag_position_requested(self, point_index: int, scene_position: QPointF):
        self.state.move_free_point(point_index=point_index, position=scene_position)

        self._update_scene_items()

    def _handle_drag_cancelled(self, point_index: int, original_position: QPointF):
        self.state.move_free_point(point_index=point_index, position=original_position)

        self._update_scene_items()

    def _update_scene_items(self, include_preview: bool = False):
        self._update_start_handle()
        self._update_end_handle(include_preview=include_preview)

        start_position = None

        if self.state.start_point is not None:
            start_position = QPointF(self.state.start_point.position)

        end_position = self.state.display_end_position

        if start_position is None or end_position is None:
            self.line_item.clear()
            self.result_item.clear()
            return

        self.line_item.set_points(start_position=start_position, end_position=end_position)

        result = self.state.calculate_result(include_preview=include_preview)

        if result is None:
            self.result_item.clear()
            return

        self.result_item.set_text(result.display_text)

        label_position = self._calculate_label_position(start_position, end_position)

        self.result_item.setPos(label_position)

        self.measurement_changed.emit(result)

    def _update_start_handle(self):
        measurement_point = self.state.start_point

        if measurement_point is None:
            self.start_handle.setVisible(False)
            return

        self.start_handle.set_scene_position(measurement_point.position)

        self.start_handle.set_movable(measurement_point.is_free_point)

        self.start_handle.setVisible(True)

    def _update_end_handle(self, include_preview: bool):
        measurement_point = self.state.end_point

        if measurement_point is not None:
            self.end_handle.set_scene_position(measurement_point.position)

            self.end_handle.set_movable(measurement_point.is_free_point)

            self.end_handle.setVisible(True)

            return

        if include_preview and self.state.preview_position is not None:
            self.end_handle.set_scene_position(self.state.preview_position)

            self.end_handle.set_movable(False)

            self.end_handle.setVisible(True)

            return

        self.end_handle.setVisible(False)

    def _clear_scene_items(self):
        if self.start_handle is not None:
            self.start_handle.setVisible(False)

        if self.end_handle is not None:
            self.end_handle.setVisible(False)

        if self.line_item is not None:
            self.line_item.clear()

        if self.result_item is not None:
            self.result_item.clear()

    def _remove_item_from_scene(self, graphics_item):
        if graphics_item is None:
            return

        if graphics_item.scene() is self.scene:
            self.scene.removeItem(graphics_item)

    def _validate_active_mode(self):
        if not self.is_active:
            raise ValueError("Der Messmodus ist nicht aktiv.")

    @staticmethod
    def _calculate_label_position(start_position: QPointF, end_position: QPointF) -> QPointF:
        midpoint = QPointF(
            (start_position.x() + end_position.x()) / 2.0,
            (start_position.y() + end_position.y()) / 2.0,
        )

        return midpoint

    @staticmethod
    def _is_position_near_point(
        scene_position: QPointF, point_position: QPointF, scene_tolerance: float
    ) -> bool:
        delta_x = scene_position.x() - point_position.x()

        delta_z = scene_position.y() - point_position.y()

        return delta_x * delta_x + delta_z * delta_z <= scene_tolerance * scene_tolerance
