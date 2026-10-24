from PySide6.QtCore import (
    QPoint,
    QRectF,
    QTimer,
    Qt,
    Signal
)

from PySide6.QtWidgets import (
    QApplication,
    QGraphicsView
)

from ui.interaction_mode import InteractionMode
from items.node_item import NodeItem

class MapView(QGraphicsView):

    zoom_changed = Signal(float)
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

    def __init__(self):
        super().__init__()

        self.setMouseTracking(
            True
        )

        self.viewport().setMouseTracking(
            True
        )

        self.interaction_mode = (
            InteractionMode.NAVIGATE
        )

        self.left_mouse_pressed = False
        self.left_drag_active = False

        self.left_press_position = QPoint()
        self.last_pan_position = QPoint()

        self.setTransformationAnchor(
            QGraphicsView.NoAnchor
        )

        self.setResizeAnchor(
            QGraphicsView.AnchorViewCenter
        )

        self.viewport_update_timer = QTimer(
            self
        )

        self.viewport_update_timer.setSingleShot(
            True
        )

        self.viewport_update_timer.setInterval(
            50
        )

        self.viewport_update_timer.timeout.connect(
            self._emit_visible_scene_rect
        )

        self.horizontalScrollBar().valueChanged.connect(
            self._schedule_viewport_update
        )

        self.verticalScrollBar().valueChanged.connect(
            self._schedule_viewport_update
        )

        self._apply_interaction_mode()

    @property
    def zoom_level(self) -> float:
        return self.transform().m11()

    def _scale_at_view_position(
        self,
        scale_factor,
        view_position
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

    def wheelEvent(self, event):
        wheel_delta = event.angleDelta().y()

        if wheel_delta == 0:
            event.ignore()
            return

        current_zoom = self.zoom_level

        if current_zoom <= 0:
            event.ignore()
            return

        if wheel_delta > 0:
            requested_factor = self.ZOOM_FACTOR

        else:
            requested_factor = (
                1.0 / self.ZOOM_FACTOR
            )

        requested_zoom = (
            current_zoom
            * requested_factor
        )

        target_zoom = max(
            self.MIN_ZOOM,
            min(
                requested_zoom,
                self.MAX_ZOOM
            )
        )

        applied_factor = (
            target_zoom
            / current_zoom
        )

        if abs(
            applied_factor - 1.0
        ) < 0.000001:
            event.accept()
            return

        self._scale_at_view_position(
            applied_factor,
            event.position().toPoint()
        )

        self.zoom_changed.emit(
            self.zoom_level
        )

        self._schedule_viewport_update()

        event.accept()

    def fitInView(self, *args):
        super().fitInView(
            *args
        )

        self.zoom_changed.emit(
            self.zoom_level
        )

        self._schedule_viewport_update()

    def resizeEvent(self, event):
        super().resizeEvent(
            event
        )

        self._schedule_viewport_update()

    def set_zoom_level(
        self,
        zoom_level
    ):
        zoom_level = float(
            zoom_level
        )

        target_zoom = max(
            self.MIN_ZOOM,
            min(
                zoom_level,
                self.MAX_ZOOM
            )
        )

        current_zoom = self.zoom_level

        if current_zoom <= 0:
            raise ValueError(
                "Der aktuelle Zoomfaktor ist ungültig."
            )

        applied_factor = (
            target_zoom
            / current_zoom
        )

        if abs(applied_factor - 1.0) < 0.000001:
            return

        self._scale_at_view_position(
            applied_factor,
            self.viewport().rect().center()
        )

        self.zoom_changed.emit(
            self.zoom_level
        )

        self._schedule_viewport_update()

    def get_visible_scene_rect(self) -> QRectF:
        return self.mapToScene(
            self.viewport().rect()
        ).boundingRect()

    def _schedule_viewport_update(
        self,
        *args
    ):
        self.viewport_update_timer.start()

    def _emit_visible_scene_rect(self):
        self.visible_scene_rect_changed.emit(
            self.get_visible_scene_rect()
        )

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

        if interaction_mode == self.interaction_mode:
            return

        self.interaction_mode = interaction_mode

        self._apply_interaction_mode()

        self.interaction_mode_changed.emit(
            interaction_mode
        )

    def get_interaction_mode(
        self
    ) -> InteractionMode:
        return self.interaction_mode

    def _apply_interaction_mode(self):
        self.setInteractive(
            False
        )

        self.setDragMode(
            QGraphicsView.NoDrag
        )

        if (
            self.interaction_mode
            == InteractionMode.NAVIGATE
        ):
            self.viewport().setCursor(
                Qt.OpenHandCursor
            )

            return

        if (
            self.interaction_mode
            == InteractionMode.SELECT
        ):
            self._restore_interaction_cursor()

    def _restore_interaction_cursor(
        self,
        view_position=None
    ):
        if view_position is None:
            view_position = (
                self.viewport()
                .mapFromGlobal(
                    self.cursor().pos()
                )
            )

        self._update_hover_cursor(
            view_position
        )

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton:
            super().mousePressEvent(
                event
            )

            return

        mouse_position = (
            event.position().toPoint()
        )

        self.left_mouse_pressed = True
        self.left_drag_active = False

        self.left_press_position = QPoint(
            mouse_position
        )

        self.last_pan_position = QPoint(
            mouse_position
        )

        event.accept()

    def mouseMoveEvent(self, event):
        mouse_position = (
            event.position().toPoint()
        )

        if (
            not self.left_mouse_pressed
            or not (
                event.buttons()
                & Qt.LeftButton
            )
        ):
            self._update_hover_cursor(
                mouse_position
            )

            super().mouseMoveEvent(
                event
            )

            return

        if not self.left_drag_active:
            drag_distance = (
                mouse_position
                - self.left_press_position
            ).manhattanLength()

            if (
                drag_distance
                < QApplication.startDragDistance()
            ):
                event.accept()
                return

            self.left_drag_active = True

            self.viewport().setCursor(
                Qt.ClosedHandCursor
            )

            self.last_pan_position = QPoint(
                mouse_position
            )

            event.accept()
            return

        movement = (
            mouse_position
            - self.last_pan_position
        )

        self.horizontalScrollBar().setValue(
            self.horizontalScrollBar().value()
            - movement.x()
        )

        self.verticalScrollBar().setValue(
            self.verticalScrollBar().value()
            - movement.y()
        )

        self.last_pan_position = QPoint(
            mouse_position
        )

        event.accept()

    def mouseReleaseEvent(self, event):
        if (
            event.button() != Qt.LeftButton
            or not self.left_mouse_pressed
        ):
            super().mouseReleaseEvent(
                event
            )

            return

        mouse_position = (
            event.position().toPoint()
        )

        was_dragging = self.left_drag_active

        self.left_mouse_pressed = False
        self.left_drag_active = False

        self._restore_interaction_cursor(
            mouse_position
        )

        if (
            not was_dragging
            and self.interaction_mode
            == InteractionMode.SELECT
        ):
            self.selection_click_requested.emit(
                mouse_position,
                event.modifiers()
            )

        event.accept()

    def _has_selectable_item_at(
        self,
        view_position
    ):
        for item in self.items(
            view_position
        ):
            if isinstance(
                item,
                NodeItem
            ):
                return True

        return False

    def _update_hover_cursor(
        self,
        view_position
    ):
        if self.left_drag_active:
            self.viewport().setCursor(
                Qt.ClosedHandCursor
            )

            return

        if (
            self.interaction_mode
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