from collections.abc import Callable

from PySide6.QtCore import QObject, QPoint, QPointF, Signal
from PySide6.QtWidgets import QGraphicsScene

from autodrive_editor.i18n import tr
from autodrive_editor.measurement.calculations import calculate_horizontal_alignment_rotation
from autodrive_editor.measurement.mode import MeasurementMode
from autodrive_editor.measurement.point import MeasurementPoint
from autodrive_editor.measurement.state import MeasurementState
from autodrive_editor.model.autodrive_data import NodeData
from autodrive_editor.rendering.items.measurement_handle_item import MeasurementHandleItem
from autodrive_editor.rendering.items.measurement_line_item import MeasurementLineItem
from autodrive_editor.rendering.items.measurement_result_item import MeasurementResultItem
from autodrive_editor.ui.map_view.map_view import MapView
from autodrive_editor.ui.map_view.zoom_controller import ViewZoomController


class MeasurementCoordinator(QObject):
    """Distance and angle measurement between points A and B. Clicks set the points and snap
    them to nodes, free points can be dragged, and the result is drawn on the map and reported
    in the status bar."""

    status_changed = Signal(str)

    measurement_mode_changed = Signal(object)

    alignment_available_changed = Signal(bool)

    # How close to a free point a press grabs it, in pixels.
    GRAB_DISTANCE_PX = 12.0

    def __init__(
        self,
        view: MapView,
        scene: QGraphicsScene,
        node_provider: Callable[[QPoint], NodeData | None],
        parent=None,
    ):
        super().__init__(parent)

        self.view = view
        self.scene = scene
        self._node_provider = node_provider

        self.state = MeasurementState()

        # Index of the dragged point, where it was before the drag, and
        # its offset from the mouse.
        self._drag_index: int | None = None
        self._drag_origin = QPointF()
        self._drag_offset = QPointF()

        self._items = None
        self._update_scene_items()

    @property
    def mode(self) -> MeasurementMode:
        return self.state.mode

    @property
    def is_complete(self) -> bool:
        return self.state.is_complete

    @property
    def is_point_dragging(self) -> bool:
        return self._drag_index is not None

    def set_mode(self, measurement_mode: MeasurementMode):
        self._drag_index = None

        if measurement_mode == MeasurementMode.INACTIVE:
            self.state.deactivate()
            status = tr("Measuring tool turned off")
        else:
            self.state.activate(measurement_mode)

            if measurement_mode == MeasurementMode.DISTANCE:
                status = tr("Distance measurement active: set point A")
            else:
                status = tr("Angle measurement active: set point A")

        self.view.set_measurement_active(self.state.is_active)
        self._update_scene_items()
        self.measurement_mode_changed.emit(measurement_mode)
        self.status_changed.emit(status)

    def handle_press(self, view_position: QPoint, modifiers):
        if not self.state.is_active:
            return

        scene_position = self.view.mapToScene(view_position)
        point_index = self._free_point_at(scene_position)

        if point_index is None:
            return

        point = self.state.get_point(point_index)
        self._drag_index = point_index
        self._drag_origin = QPointF(point.position)
        self._drag_offset = point.position - scene_position

    def handle_move(self, view_position: QPoint, modifiers):
        if not self.state.is_active:
            return

        scene_position = self.view.mapToScene(view_position)

        if self.is_point_dragging:
            self.state.move_free_point(self._drag_index, scene_position + self._drag_offset)
            self._update_scene_items()

        elif self.state.is_awaiting_end_point:
            self.state.set_preview_position(self._snapped_point(view_position).position)
            self._update_scene_items()

    def handle_release(self, view_position: QPoint, modifiers):
        if not self.state.is_active:
            return

        if self.is_point_dragging:
            self.handle_move(view_position, modifiers)
            self._drag_index = None
            self.status_changed.emit(tr("Measuring point moved"))
            return

        measurement_point = self._snapped_point(view_position)

        if self.state.is_awaiting_end_point:
            self.state.set_end_point(measurement_point)
            self._update_scene_items()

            result = self.state.calculate_result()

            if result is not None:
                self.status_changed.emit(tr("Measurement: {result}", result=result.display_text))
            else:
                self.status_changed.emit(tr("Point B set"))
            return

        self.state.set_start_point(measurement_point)
        self._update_scene_items()
        self.status_changed.emit(tr("Point A set"))

    def cancel(self):
        """Esc: cancels a point drag, else clears the measurement, else ends measuring."""

        if not self.state.is_active:
            return

        if self.is_point_dragging:
            self._cancel_drag()
            self.status_changed.emit(tr("Moving the measuring point cancelled"))

        elif self.state.has_start_point:
            self.state.clear_points()
            self._update_scene_items()
            self.status_changed.emit(tr("Measurement cleared: set point A"))

        else:
            self.set_mode(MeasurementMode.INACTIVE)

    def align_view_to_measurement(self):
        if not self.state.is_complete:
            self.alignment_available_changed.emit(False)
            self.status_changed.emit(tr("Points A and B must be set to align the view"))
            return

        try:
            target_rotation = calculate_horizontal_alignment_rotation(
                start_position=self.state.start_point.position,
                end_position=self.state.end_point.position,
            )
        except ValueError as ex:
            self.status_changed.emit(
                tr("The measuring line could not be aligned: {error}", error=ex)
            )
            return

        self.view.set_exact_rotation_angle(target_rotation)

        self.status_changed.emit(
            tr("Measuring line aligned horizontally: rotation {angle:.2f}°", angle=target_rotation)
        )

    def remove_scene_items(self):
        """Takes the items out of the scene before the scene is cleared."""

        if self.is_point_dragging:
            self._cancel_drag()

        if self._items is not None:
            for item in self._items:
                if item.scene() is self.scene:
                    self.scene.removeItem(item)

        self._items = None

    def restore_scene_items(self):
        if self.state.is_active:
            self._update_scene_items()

    def _cancel_drag(self):
        self.state.move_free_point(self._drag_index, self._drag_origin)
        self._drag_index = None
        self._update_scene_items()

    def _snapped_point(self, view_position: QPoint) -> MeasurementPoint:
        """A point on the node under the mouse, or a free point."""

        node = self._node_provider(view_position)

        if node is not None:
            return MeasurementPoint(QPointF(node.x, node.z), node.node_id)

        return MeasurementPoint(self.view.mapToScene(view_position))

    def _free_point_at(self, scene_position: QPointF) -> int | None:
        tolerance = self.GRAB_DISTANCE_PX / max(self.view.zoom_level, ViewZoomController.MIN_ZOOM)

        for point_index in (0, 1):
            point = self.state.get_point(point_index)

            if point is None or not point.is_free_point:
                continue

            delta = scene_position - point.position

            if delta.x() ** 2 + delta.y() ** 2 <= tolerance**2:
                return point_index

        return None

    def _ensure_scene_items(self):
        """Creates the items again after the scene was cleared."""

        if self._items is not None and all(item.scene() is self.scene for item in self._items):
            return

        self.remove_scene_items()

        self._start_handle = MeasurementHandleItem(point_index=0, label="A", movable=True)
        self._end_handle = MeasurementHandleItem(point_index=1, label="B", movable=True)
        self._line_item = MeasurementLineItem()
        self._result_item = MeasurementResultItem()
        self._items = (self._line_item, self._start_handle, self._end_handle, self._result_item)

        for item in self._items:
            self.scene.addItem(item)

    def _update_scene_items(self):
        self._ensure_scene_items()

        start_point = self.state.start_point
        end_point = self.state.end_point
        end_position = self.state.display_end_position

        self._update_handle(
            self._start_handle, start_point.position if start_point else None, start_point
        )
        self._update_handle(self._end_handle, end_position, end_point)

        result = self.state.calculate_result(include_preview=True)

        if start_point is None or end_position is None:
            self._line_item.clear()
        else:
            self._line_item.set_points(
                start_position=start_point.position, end_position=end_position
            )

        if result is None:
            self._result_item.clear()
        else:
            self._result_item.set_text(result.display_text)
            self._result_item.setPos((start_point.position + end_position) / 2.0)

        self.alignment_available_changed.emit(self.state.is_complete)

    @staticmethod
    def _update_handle(handle, position: QPointF | None, point: MeasurementPoint | None):
        """Shows the handle at the position; only set free points look movable."""

        handle.setVisible(position is not None)

        if position is not None:
            handle.set_scene_position(position)
            handle.set_movable(point is not None and point.is_free_point)
