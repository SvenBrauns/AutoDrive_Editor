from PySide6.QtCore import (
    QRectF,
    QTimer,
    Signal
)
from PySide6.QtWidgets import QGraphicsView

from ui.interaction_mode import InteractionMode

class MapView(QGraphicsView):

    zoom_changed = Signal(float)
    visible_scene_rect_changed = Signal(
        QRectF
    )
    interaction_mode_changed = Signal(
        object
    )
    ZOOM_FACTOR = 1.15
    MIN_ZOOM = 0.02
    MAX_ZOOM = 50.0

    def __init__(self):
        super().__init__()

        self.interaction_mode = (
            InteractionMode.NAVIGATE
        )

        self.setDragMode(
            QGraphicsView.ScrollHandDrag
        )

        self.setTransformationAnchor(
            QGraphicsView.AnchorUnderMouse
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

    @property
    def zoom_level(self) -> float:
        return self.transform().m11()

    def wheelEvent(self, event):
        wheel_delta = event.angleDelta().y()

        if wheel_delta == 0:
            event.ignore()
            return

        current_zoom = self.zoom_level

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

        if current_zoom <= 0:
            return

        applied_factor = (
            target_zoom
            / current_zoom
        )

        if abs(applied_factor - 1.0) < 0.000001:
            event.accept()
            return

        self.scale(
            applied_factor,
            applied_factor
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

        self.scale(
            applied_factor,
            applied_factor
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

        self.interaction_mode_changed.emit(
            interaction_mode
        )


    def get_interaction_mode(
        self
    ) -> InteractionMode:
        return self.interaction_mode