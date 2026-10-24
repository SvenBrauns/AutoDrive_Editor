import math
from dataclasses import dataclass, field

from PySide6.QtCore import (
    QPoint,
    QRectF,
    QTimer,
    Qt,
    Signal
)
from PySide6.QtGui import (
    QCursor,
    QMouseEvent,
    QResizeEvent,
    QWheelEvent
)
from PySide6.QtWidgets import (
    QApplication,
    QGraphicsItem,
    QGraphicsView
)

from ui.interaction_mode import InteractionMode


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

    ZOOM_FACTOR = 1.15
    MIN_ZOOM = 0.02
    MAX_ZOOM = 50.0

    VIEWPORT_UPDATE_DELAY_MS = 50
    ZOOM_COMPARISON_TOLERANCE = 0.000001

    ROTATION_DEGREES_PER_PIXEL = 0.3
    ROTATION_COMPARISON_TOLERANCE = 0.000001

    def __init__(self):
        super().__init__()

        self._interaction_mode = (
            InteractionMode.NAVIGATE
        )

        self._rotation_angle = 0.0

        self._pointer_state = (
            PointerDragState()
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
        return self._rotation_angle

    @property
    def interaction_mode(
        self
    ) -> InteractionMode:
        return self._interaction_mode

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

    def reset_view_rotation(self):
        if (
            abs(self._rotation_angle)
            < self.ROTATION_COMPARISON_TOLERANCE
        ):
            return

        viewport_center = (
            self.viewport()
            .rect()
            .center()
        )

        scene_center = self.mapToScene(
            viewport_center
        )

        self.rotate(
            -self._rotation_angle
        )

        self._rotation_angle = 0.0

        self.centerOn(
            scene_center
        )

        self.rotation_changed.emit(
            self._rotation_angle
        )

        self._schedule_viewport_update()

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
        if event.button() not in (
            Qt.LeftButton,
            Qt.MiddleButton
        ):
            super().mousePressEvent(
                event
            )
            return

        mouse_position = (
            event.position().toPoint()
        )

        self._pointer_state.begin(
            button=event.button(),
            position=mouse_position
        )

        if event.button() == Qt.MiddleButton:
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

        mouse_position = (
            event.position().toPoint()
        )

        was_dragging = (
            self._pointer_state.drag_active
        )

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

        rotation_delta = (
            movement.x()
            * self.ROTATION_DEGREES_PER_PIXEL
        )

        self._pointer_state.last_position = QPoint(
            mouse_position
        )

        if (
            abs(rotation_delta)
            < self.ROTATION_COMPARISON_TOLERANCE
        ):
            return

        self._rotate_around_viewport_center(
            rotation_delta
        )

    def _rotate_around_viewport_center(
        self,
        rotation_delta: float
    ):
        viewport_center = (
            self.viewport()
            .rect()
            .center()
        )

        scene_center = self.mapToScene(
            viewport_center
        )

        self.rotate(
            rotation_delta
        )

        self._rotation_angle = (
            self._normalize_rotation_angle(
                self._rotation_angle
                + rotation_delta
            )
        )

        self.centerOn(
            scene_center
        )

        self.rotation_changed.emit(
            self._rotation_angle
        )

        self._schedule_viewport_update()

    @staticmethod
    def _normalize_rotation_angle(
        rotation_angle: float
    ) -> float:
        normalized_angle = (
            rotation_angle + 180.0
        ) % 360.0 - 180.0

        if abs(normalized_angle) < 0.000001:
            return 0.0

        return normalized_angle

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

            else:
                self.viewport().setCursor(
                    Qt.ClosedHandCursor
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