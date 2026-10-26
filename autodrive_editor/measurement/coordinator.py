from collections.abc import Callable

from PySide6.QtCore import QObject, QPoint, QPointF, Signal

from autodrive_editor.i18n import tr
from autodrive_editor.measurement.calculations import calculate_horizontal_alignment_rotation
from autodrive_editor.measurement.controller import MeasurementController
from autodrive_editor.measurement.mode import MeasurementMode
from autodrive_editor.measurement.point import MeasurementPoint
from autodrive_editor.rendering.items.node_item import NodeItem
from autodrive_editor.ui.map_view.map_view import MapView
from autodrive_editor.ui.map_view.zoom_controller import ViewZoomController


class MeasurementCoordinator(QObject):
    """Turns map clicks into measurement points, snaps them to nodes and reports results in the
    status bar.
    """

    status_changed = Signal(str)

    measurement_mode_changed = Signal(object)

    alignment_available_changed = Signal(bool)

    def __init__(
        self,
        view: MapView,
        controller: MeasurementController,
        node_item_provider: Callable[[QPoint], NodeItem | None],
        parent=None,
    ):
        super().__init__(parent)

        if not isinstance(view, MapView):
            raise TypeError("Invalid map view.")

        if not isinstance(controller, MeasurementController):
            raise TypeError("Invalid MeasurementController.")

        if not callable(node_item_provider):
            raise TypeError("Invalid NodeItem provider.")

        self.view = view
        self.controller = controller

        self._node_item_provider = node_item_provider

        self._measurement_drag_active = False

        self._connect_controller_signals()

    @property
    def mode(self) -> MeasurementMode:
        return self.controller.mode

    @property
    def is_active(self) -> bool:
        return self.controller.is_active

    @property
    def is_complete(self) -> bool:
        return self.controller.is_complete

    @property
    def is_point_dragging(self) -> bool:
        """True while a measurement point is being dragged."""

        return self._measurement_drag_active

    def set_mode(self, measurement_mode: MeasurementMode):
        if not isinstance(measurement_mode, MeasurementMode):
            raise TypeError("Invalid measurement mode.")

        self._reset_drag_state()

        if measurement_mode == MeasurementMode.INACTIVE:
            self.controller.deactivate()

            self.view.set_measurement_active(False)

            self.measurement_mode_changed.emit(MeasurementMode.INACTIVE)

            self.alignment_available_changed.emit(False)

            self.status_changed.emit(tr("Measuring tool turned off"))

            return

        self.controller.activate(measurement_mode)

        self.view.set_measurement_active(True)

        self.measurement_mode_changed.emit(measurement_mode)

        self.alignment_available_changed.emit(False)

        if measurement_mode == MeasurementMode.DISTANCE:
            self.status_changed.emit(tr("Distance measurement active: set point A"))

        elif measurement_mode == MeasurementMode.ANGLE:
            self.status_changed.emit(tr("Angle measurement active: set point A"))

    def handle_press(self, view_position: QPoint, modifiers):
        if not self.controller.is_active:
            return

        scene_position = self.view.mapToScene(view_position)

        scene_tolerance = 12.0 / max(self.view.zoom_level, ViewZoomController.MIN_ZOOM)

        handle_index = self.controller.get_handle_at_scene_position(
            scene_position=scene_position, scene_tolerance=scene_tolerance
        )

        if handle_index is None:
            self._set_drag_active(False)

            return

        drag_started = self.controller.begin_point_drag(
            point_index=handle_index, press_scene_position=scene_position
        )

        self._set_drag_active(drag_started)

    def handle_move(self, view_position: QPoint, modifiers):
        if not self.controller.is_active:
            return

        scene_position = self.view.mapToScene(view_position)

        if self._measurement_drag_active:
            self.controller.update_point_drag(scene_position)

            return

        if self.controller.state.is_awaiting_end_point:
            preview_position = self._get_preview_position(
                view_position=view_position, scene_position=scene_position
            )

            self.controller.set_preview_position(preview_position)

    def handle_release(self, view_position: QPoint, modifiers):
        if not self.controller.is_active:
            return

        scene_position = self.view.mapToScene(view_position)

        if self._measurement_drag_active:
            self.controller.update_point_drag(scene_position)

            self.controller.finish_point_drag()

            self._set_drag_active(False)

            self.status_changed.emit(tr("Measuring point moved"))

            return

        measurement_point = self._create_measurement_point(
            view_position=view_position, scene_position=scene_position
        )

        measurement_state = self.controller.state

        if measurement_state.is_awaiting_start_point or measurement_state.is_complete:
            self.controller.set_start_point(measurement_point)

            self.status_changed.emit(tr("Point A set"))

            return

        if measurement_state.is_awaiting_end_point:
            self.controller.set_end_point(measurement_point)

            measurement_result = self.controller.state.calculate_result()

            if measurement_result is not None:
                self.status_changed.emit(
                    tr("Measurement: {result}", result=measurement_result.display_text)
                )

            else:
                self.status_changed.emit(tr("Point B set"))

    def cancel(self):
        if not self.controller.is_active:
            return

        if self.controller.is_dragging:
            self.controller.cancel_drag()

            self._set_drag_active(False)

            self.status_changed.emit(tr("Moving the measuring point cancelled"))

            return

        if self.controller.state.has_start_point:
            self.controller.clear_measurement()

            self.status_changed.emit(tr("Measurement cleared: set point A"))

            return

        self.set_mode(MeasurementMode.INACTIVE)

    def align_view_to_measurement(self):
        measurement_state = self.controller.state

        if not measurement_state.is_complete:
            self.alignment_available_changed.emit(False)

            self.status_changed.emit(tr("Points A and B must be set to align the view"))

            return

        start_point = measurement_state.start_point
        end_point = measurement_state.end_point

        if start_point is None or end_point is None:
            self.alignment_available_changed.emit(False)

            return

        try:
            target_rotation = calculate_horizontal_alignment_rotation(
                start_position=start_point.position, end_position=(end_point.position)
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
        self._reset_drag_state()

        self.controller.remove_scene_items()

    def restore_scene_items(self):
        self.controller.restore_scene_items()

        self._update_alignment_availability()

    def _create_measurement_point(
        self, view_position: QPoint, scene_position: QPointF
    ) -> MeasurementPoint:
        node_item = self._get_node_item(view_position)

        if node_item is not None:
            return MeasurementPoint.create_node_anchor(
                node_id=node_item.node_data.node_id, position=node_item.scenePos()
            )

        return MeasurementPoint.create_free(scene_position)

    def _get_preview_position(self, view_position: QPoint, scene_position: QPointF) -> QPointF:
        node_item = self._get_node_item(view_position)

        if node_item is not None:
            return QPointF(node_item.scenePos())

        return QPointF(scene_position)

    def _get_node_item(self, view_position: QPoint) -> NodeItem | None:
        node_item = self._node_item_provider(view_position)

        if node_item is None:
            return None

        if not isinstance(node_item, NodeItem):
            raise TypeError("The NodeItem provider returned an invalid object.")

        return node_item

    def _set_drag_active(self, active: bool):
        self._measurement_drag_active = bool(active)

    def _reset_drag_state(self):
        if self.controller.is_dragging:
            self.controller.cancel_drag()

        self._set_drag_active(False)

    def _connect_controller_signals(self):
        self.controller.measurement_changed.connect(self._update_alignment_availability)

        self.controller.measurement_cleared.connect(self._update_alignment_availability)

        self.controller.mode_changed.connect(self._update_alignment_availability)

    def _update_alignment_availability(self, *args):
        alignment_available = self.controller.is_active and self.controller.is_complete

        self.alignment_available_changed.emit(alignment_available)
