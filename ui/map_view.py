import math
from dataclasses import dataclass, field

from PySide6.QtCore import (
    QPoint,
    QRect,
    QRectF,
    QTimer,
    Qt,
    Signal
)
from PySide6.QtGui import (
    QCursor,
    QMouseEvent,
    QPainterPath,
    QResizeEvent,
    QWheelEvent,
    QKeyEvent
)
from PySide6.QtWidgets import (
    QApplication,
    QGraphicsItem,
    QGraphicsView,
    QRubberBand
)

from ui.interaction_mode import InteractionMode
from ui.view_rotation_controller import (
    ViewRotationController
)


@dataclass
class PointerDragState:

    pressed_button: Qt.MouseButton = Qt.NoButton
    drag_active: bool = False

    press_position: QPoint = field(
        default_factory=QPoint
    )

    last_position: QPoint = field(
        default_factory=QPoint
    )

    def begin(
        self,
        button: Qt.MouseButton,
        position: QPoint
    ):
        self.pressed_button = button
        self.drag_active = False

        self.press_position = QPoint(
            position
        )

        self.last_position = QPoint(
            position
        )

    def reset(self):
        self.pressed_button = Qt.NoButton
        self.drag_active = False

        self.press_position = QPoint()
        self.last_position = QPoint()


class MapView(QGraphicsView):

    zoom_changed = Signal(
        float
    )

    rotation_changed = Signal(
        float
    )

    rotation_step_changed = Signal(
        float
    )

    visible_scene_rect_changed = Signal(
        QRectF
    )

    interaction_mode_changed = Signal(
        object
    )

    selection_click_requested = Signal(
        QPoint,
        object
    )

    selection_area_requested = Signal(
        object,
        object
    )

    selection_area_preview_requested = Signal(
        object,
        object
    )

    selection_area_preview_cleared = Signal()

    measurement_press_requested = Signal(
        QPoint,
        object
    )

    measurement_move_requested = Signal(
        QPoint,
        object
    )

    measurement_release_requested = Signal(
        QPoint,
        object
    )

    measurement_cancel_requested = Signal()

    ZOOM_FACTOR = 1.15
    MIN_ZOOM = 0.02
    MAX_ZOOM = 50.0

    VIEWPORT_UPDATE_DELAY_MS = 50
    ZOOM_COMPARISON_TOLERANCE = 0.000001

    ROTATION_DEGREES_PER_PIXEL = (
        ViewRotationController
        .ROTATION_DEGREES_PER_PIXEL
    )

    ROTATION_COMPARISON_TOLERANCE = (
        ViewRotationController
        .ROTATION_COMPARISON_TOLERANCE
    )

    DEFAULT_ROTATION_STEP = (
        ViewRotationController
        .DEFAULT_ROTATION_STEP
    )

    def __init__(self):
        super().__init__()

        self._interaction_mode = (
            InteractionMode.NAVIGATE
        )

        self._measurement_active = False
        self._measurement_point_drag_active = False

        self._pointer_state = (
            PointerDragState()
        )

        self._selection_rubber_band = QRubberBand(
            QRubberBand.Rectangle,
            self.viewport()
        )

        self._selection_rubber_band.hide()

        self._rotation_controller = (
            ViewRotationController(
                view=self,
                viewport_update_callback=(
                    self._schedule_viewport_update
                ),
                parent=self
            )
        )

        self._rotation_controller.rotation_changed.connect(
            self.rotation_changed.emit
        )

        self._rotation_controller.rotation_step_changed.connect(
            self.rotation_step_changed.emit
        )

        self._configure_view()
        self._create_viewport_update_timer()
        self._connect_scrollbars()

        self._apply_interaction_mode()

    @property
    def zoom_level(self) -> float:
        view_transform = self.transform()

        return math.hypot(
            view_transform.m11(),
            view_transform.m12()
        )

    @property
    def rotation_angle(self) -> float:
        return (
            self._rotation_controller
            .rotation_angle
        )

    @property
    def rotation_step(self) -> float:
        return (
            self._rotation_controller
            .rotation_step
        )

    @property
    def interaction_mode(
        self
    ) -> InteractionMode:
        return self._interaction_mode

    @property
    def measurement_active(self) -> bool:
        return self._measurement_active

    def set_zoom_level(
        self,
        zoom_level
    ):
        target_zoom = self._clamp_zoom(
            zoom_level
        )

        current_zoom = self.zoom_level

        if current_zoom <= 0:
            raise ValueError(
                "Der aktuelle Zoomfaktor ist ungültig."
            )

        scale_factor = (
            target_zoom
            / current_zoom
        )

        if self._is_neutral_scale(
            scale_factor
        ):
            return

        self._scale_at_view_position(
            scale_factor=scale_factor,
            view_position=(
                self.viewport()
                .rect()
                .center()
            )
        )

        self._notify_view_transform_changed()

    def set_rotation_angle(
        self,
        rotation_angle: float
    ):
        self._rotation_controller.set_rotation_angle(
            rotation_angle
        )

    def set_exact_rotation_angle(
        self,
        rotation_angle: float
    ):
        self._rotation_controller.set_exact_rotation_angle(
            rotation_angle
        )

    def set_rotation_step(
        self,
        rotation_step: float
    ):
        self._rotation_controller.set_rotation_step(
            rotation_step
        )

    def reset_view_rotation(self):
        self._rotation_controller.reset_rotation()

    def set_interaction_mode(
        self,
        interaction_mode: InteractionMode
    ):
        if not isinstance(
            interaction_mode,
            InteractionMode
        ):
            raise TypeError(
                "Der Interaktionsmodus ist ungültig."
            )

        if (
            interaction_mode
            == self._interaction_mode
        ):
            return

        self._interaction_mode = (
            interaction_mode
        )

        self._apply_interaction_mode()

        self.interaction_mode_changed.emit(
            interaction_mode
        )

    def set_measurement_active(
        self,
        active: bool
    ):
        active = bool(
            active
        )

        if active == self._measurement_active:
            return

        self._measurement_active = active
        self._measurement_point_drag_active = False

        self._selection_rubber_band.hide()
        self._pointer_state.reset()

        self._restore_interaction_cursor()

    def set_measurement_point_drag_active(
        self,
        active: bool
    ):
        self._measurement_point_drag_active = bool(
            active
        )

    def get_visible_scene_rect(
        self
    ) -> QRectF:
        return self.mapToScene(
            self.viewport().rect()
        ).boundingRect()

    def fitInView(
        self,
        *args
    ):
        super().fitInView(
            *args
        )

        self._notify_view_transform_changed()

    def wheelEvent(
        self,
        event: QWheelEvent
    ):
        wheel_delta = event.angleDelta().y()

        if wheel_delta == 0:
            event.ignore()
            return

        current_zoom = self.zoom_level

        if current_zoom <= 0:
            event.ignore()
            return

        if wheel_delta > 0:
            requested_factor = (
                self.ZOOM_FACTOR
            )

        else:
            requested_factor = (
                1.0 / self.ZOOM_FACTOR
            )

        target_zoom = self._clamp_zoom(
            current_zoom
            * requested_factor
        )

        scale_factor = (
            target_zoom
            / current_zoom
        )

        if self._is_neutral_scale(
            scale_factor
        ):
            event.accept()
            return

        self._scale_at_view_position(
            scale_factor=scale_factor,
            view_position=(
                event.position().toPoint()
            )
        )

        self._notify_view_transform_changed()

        event.accept()

    def resizeEvent(
        self,
        event: QResizeEvent
    ):
        super().resizeEvent(
            event
        )

        self._schedule_viewport_update()

    def mousePressEvent(
        self,
        event: QMouseEvent
    ):
        pressed_button = event.button()

        mouse_position = (
            event.position().toPoint()
        )

        if (
            self._measurement_active
            and pressed_button == Qt.LeftButton
        ):
            self._pointer_state.begin(
                button=pressed_button,
                position=mouse_position
            )

            self._measurement_point_drag_active = False

            self.measurement_press_requested.emit(
                mouse_position,
                event.modifiers()
            )

            event.accept()
            return

        supported_button = (
            pressed_button
            in (
                Qt.LeftButton,
                Qt.MiddleButton
            )
        )

        right_selection_button = (
            pressed_button == Qt.RightButton
            and self._interaction_mode
            == InteractionMode.SELECT
            and not self._measurement_active
        )

        if (
            not supported_button
            and not right_selection_button
        ):
            super().mousePressEvent(
                event
            )
            return

        self._pointer_state.begin(
            button=pressed_button,
            position=mouse_position
        )

        if pressed_button == Qt.MiddleButton:
            self.viewport().setCursor(
                Qt.SizeAllCursor
            )

        event.accept()

    def mouseMoveEvent(
        self,
        event: QMouseEvent
    ):
        mouse_position = (
            event.position().toPoint()
        )

        if self._is_button_drag(
            event,
            Qt.MiddleButton
        ):
            self._handle_rotation_drag(
                mouse_position
            )

            event.accept()
            return

        if self._measurement_active:
            if self._is_button_drag(
                event,
                Qt.LeftButton
            ):
                if self._measurement_point_drag_active:
                    if (
                        not self._pointer_state.drag_active
                        and not self._drag_threshold_reached(
                            mouse_position
                        )
                    ):
                        event.accept()
                        return

                    self._pointer_state.drag_active = True

                    self.measurement_move_requested.emit(
                        mouse_position,
                        event.modifiers()
                    )

                    self._update_hover_cursor(
                        mouse_position
                    )

                    event.accept()
                    return

                self._handle_pan_drag(
                    mouse_position
                )

                event.accept()
                return

            self.measurement_move_requested.emit(
                mouse_position,
                event.modifiers()
            )

            self._update_hover_cursor(
                mouse_position
            )

            event.accept()
            return

        if self._is_button_drag(
            event,
            Qt.RightButton
        ):
            self._handle_selection_area_drag(
                mouse_position=mouse_position,
                modifiers=event.modifiers()
            )

            event.accept()
            return

        if self._is_button_drag(
            event,
            Qt.LeftButton
        ):
            self._handle_pan_drag(
                mouse_position
            )

            event.accept()
            return

        self._update_hover_cursor(
            mouse_position
        )

        super().mouseMoveEvent(
            event
        )

    def mouseReleaseEvent(
        self,
        event: QMouseEvent
    ):
        mouse_position = (
            event.position().toPoint()
        )

        if (
            self._measurement_active
            and event.button() == Qt.LeftButton
            and self._pointer_state.pressed_button
            == Qt.LeftButton
        ):
            was_dragging = (
                self._pointer_state.drag_active
            )

            measurement_point_drag = (
                self._measurement_point_drag_active
            )

            if measurement_point_drag:
                self.measurement_release_requested.emit(
                    mouse_position,
                    event.modifiers()
                )

            elif not was_dragging:
                self.measurement_release_requested.emit(
                    mouse_position,
                    event.modifiers()
                )

            self._measurement_point_drag_active = False

            self._pointer_state.reset()

            self._restore_interaction_cursor(
                mouse_position
            )

            event.accept()
            return

        if (
            event.button()
            != self._pointer_state.pressed_button
        ):
            super().mouseReleaseEvent(
                event
            )
            return

        released_button = (
            self._pointer_state.pressed_button
        )

        was_dragging = (
            self._pointer_state.drag_active
        )

        if (
            released_button == Qt.RightButton
            and was_dragging
        ):
            self._finish_selection_area(
                event.modifiers()
            )

        else:
            self._selection_rubber_band.hide()

            if released_button == Qt.RightButton:
                self.selection_area_preview_cleared.emit()

        self._pointer_state.reset()

        self._restore_interaction_cursor(
            mouse_position
        )

        if (
            released_button == Qt.LeftButton
            and not was_dragging
            and self._interaction_mode
            == InteractionMode.SELECT
        ):
            self.selection_click_requested.emit(
                mouse_position,
                event.modifiers()
            )

        event.accept()

    def keyPressEvent(
        self,
        event: QKeyEvent
    ):
        if (
            self._measurement_active
            and event.key() == Qt.Key_Escape
        ):
            self.measurement_cancel_requested.emit()

            event.accept()
            return

        super().keyPressEvent(
            event
        )

    def _configure_view(self):
        self.setMouseTracking(
            True
        )

        self.viewport().setMouseTracking(
            True
        )

        self.setInteractive(
            False
        )

        self.setDragMode(
            QGraphicsView.NoDrag
        )

        self.setTransformationAnchor(
            QGraphicsView.NoAnchor
        )

        self.setResizeAnchor(
            QGraphicsView.AnchorViewCenter
        )

    def _create_viewport_update_timer(self):
        self._viewport_update_timer = QTimer(
            self
        )

        self._viewport_update_timer.setSingleShot(
            True
        )

        self._viewport_update_timer.setInterval(
            self.VIEWPORT_UPDATE_DELAY_MS
        )

        self._viewport_update_timer.timeout.connect(
            self._emit_visible_scene_rect
        )

    def _connect_scrollbars(self):
        self.horizontalScrollBar().valueChanged.connect(
            self._schedule_viewport_update
        )

        self.verticalScrollBar().valueChanged.connect(
            self._schedule_viewport_update
        )

    def _apply_interaction_mode(self):
        self._restore_interaction_cursor()

    def _clamp_zoom(
        self,
        zoom_level
    ) -> float:
        zoom_level = float(
            zoom_level
        )

        return max(
            self.MIN_ZOOM,
            min(
                zoom_level,
                self.MAX_ZOOM
            )
        )

    def _is_neutral_scale(
        self,
        scale_factor: float
    ) -> bool:
        return (
            abs(
                scale_factor - 1.0
            )
            < self.ZOOM_COMPARISON_TOLERANCE
        )

    def _scale_at_view_position(
        self,
        scale_factor: float,
        view_position: QPoint
    ):
        scene_position_before = self.mapToScene(
            view_position
        )

        self.scale(
            scale_factor,
            scale_factor
        )

        scene_position_after = self.mapToScene(
            view_position
        )

        scene_delta = (
            scene_position_after
            - scene_position_before
        )

        self.translate(
            scene_delta.x(),
            scene_delta.y()
        )

    def _notify_view_transform_changed(self):
        self.zoom_changed.emit(
            self.zoom_level
        )

        self._schedule_viewport_update()

    def _is_button_drag(
        self,
        event: QMouseEvent,
        button: Qt.MouseButton
    ) -> bool:
        return (
            self._pointer_state.pressed_button
            == button
            and bool(
                event.buttons()
                & button
            )
        )

    def _drag_threshold_reached(
        self,
        mouse_position: QPoint
    ) -> bool:
        drag_distance = (
            mouse_position
            - self._pointer_state.press_position
        ).manhattanLength()

        return (
            drag_distance
            >= QApplication.startDragDistance()
        )

    def _handle_pan_drag(
        self,
        mouse_position: QPoint
    ):
        if not self._pointer_state.drag_active:
            if not self._drag_threshold_reached(
                mouse_position
            ):
                return

            self._begin_panning(
                mouse_position
            )
            return

        self._pan_to(
            mouse_position
        )

    def _handle_selection_area_drag(
        self,
        mouse_position: QPoint,
        modifiers
    ):
        if not self._pointer_state.drag_active:
            if not self._drag_threshold_reached(
                mouse_position
            ):
                return

            self._pointer_state.drag_active = True

            self.viewport().setCursor(
                Qt.CrossCursor
            )

            self._selection_rubber_band.show()

        self._update_selection_rubber_band(
            mouse_position
        )

        selection_path = (
            self._create_selection_path()
        )

        if selection_path is None:
            return

        self.selection_area_preview_requested.emit(
            selection_path,
            modifiers
        )

    def _update_selection_rubber_band(
        self,
        mouse_position: QPoint
    ):
        selection_rect = QRect(
            self._pointer_state.press_position,
            mouse_position
        ).normalized()

        self._selection_rubber_band.setGeometry(
            selection_rect
        )

    def _create_selection_path(
        self
    ) -> QPainterPath | None:
        selection_rect = (
            self._selection_rubber_band.geometry()
        )

        if (
            selection_rect.width() <= 0
            or selection_rect.height() <= 0
        ):
            return None

        scene_polygon = self.mapToScene(
            selection_rect
        )

        selection_path = QPainterPath()

        selection_path.addPolygon(
            scene_polygon
        )

        selection_path.closeSubpath()

        return selection_path

    def _finish_selection_area(
        self,
        modifiers
    ):
        selection_path = (
            self._create_selection_path()
        )

        self._selection_rubber_band.hide()

        if selection_path is not None:
            self.selection_area_requested.emit(
                selection_path,
                modifiers
            )

        self.selection_area_preview_cleared.emit()

    def _handle_rotation_drag(
        self,
        mouse_position: QPoint
    ):
        if not self._pointer_state.drag_active:
            if not self._drag_threshold_reached(
                mouse_position
            ):
                return

            self._pointer_state.drag_active = True

            self._pointer_state.last_position = QPoint(
                mouse_position
            )

            self.viewport().setCursor(
                Qt.SizeAllCursor
            )

            return

        movement = (
            mouse_position
            - self._pointer_state.last_position
        )

        self._pointer_state.last_position = QPoint(
            mouse_position
        )

        self._rotation_controller.rotate_by_horizontal_pixels(
            movement.x()
        )

    def _begin_panning(
        self,
        mouse_position: QPoint
    ):
        self._pointer_state.drag_active = True

        self._pointer_state.last_position = QPoint(
            mouse_position
        )

        self.viewport().setCursor(
            Qt.ClosedHandCursor
        )

    def _pan_to(
        self,
        mouse_position: QPoint
    ):
        movement = (
            mouse_position
            - self._pointer_state.last_position
        )

        self.horizontalScrollBar().setValue(
            self.horizontalScrollBar().value()
            - movement.x()
        )

        self.verticalScrollBar().setValue(
            self.verticalScrollBar().value()
            - movement.y()
        )

        self._pointer_state.last_position = QPoint(
            mouse_position
        )

    def _restore_interaction_cursor(
        self,
        view_position=None
    ):
        if view_position is None:
            view_position = (
                self.viewport()
                .mapFromGlobal(
                    QCursor.pos()
                )
            )

        self._update_hover_cursor(
            view_position
        )

    def _update_hover_cursor(
        self,
        view_position: QPoint
    ):
        if self._pointer_state.drag_active:
            if (
                self._pointer_state.pressed_button
                == Qt.MiddleButton
            ):
                self.viewport().setCursor(
                    Qt.SizeAllCursor
                )

            elif (
                self._pointer_state.pressed_button
                == Qt.RightButton
            ):
                self.viewport().setCursor(
                    Qt.CrossCursor
                )

            elif (
                self._measurement_active
                and self._measurement_point_drag_active
            ):
                self.viewport().setCursor(
                    Qt.SizeAllCursor
                )

            else:
                self.viewport().setCursor(
                    Qt.ClosedHandCursor
                )

            return

        if self._measurement_active:
            self.viewport().setCursor(
                Qt.CrossCursor
            )

            return

        if (
            self._interaction_mode
            == InteractionMode.NAVIGATE
        ):
            self.viewport().setCursor(
                Qt.OpenHandCursor
            )

            return

        if self._has_selectable_item_at(
            view_position
        ):
            self.viewport().setCursor(
                Qt.ArrowCursor
            )

        else:
            self.viewport().setCursor(
                Qt.OpenHandCursor
            )

    def _has_selectable_item_at(
        self,
        view_position: QPoint
    ) -> bool:
        for item in self.items(
            view_position
        ):
            if (
                item.flags()
                & QGraphicsItem.ItemIsSelectable
            ):
                return True

        return False

    def _schedule_viewport_update(
        self,
        *args
    ):
        self._viewport_update_timer.start()

    def _emit_visible_scene_rect(self):
        self.visible_scene_rect_changed.emit(
            self.get_visible_scene_rect()
        )