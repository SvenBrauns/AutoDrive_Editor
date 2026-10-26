import math

from PySide6.QtCore import QObject, QPoint, QRectF, QTimer, Signal
from PySide6.QtWidgets import QGraphicsView


class ViewZoomController(QObject):
    """Zooms the view at the mouse position and reports the visible scene area."""

    zoom_changed = Signal(float)

    visible_scene_rect_changed = Signal(QRectF)

    ZOOM_FACTOR = 1.15
    MIN_ZOOM = 0.02
    MAX_ZOOM = 50.0

    VIEWPORT_UPDATE_DELAY_MS = 50
    ZOOM_COMPARISON_TOLERANCE = 0.000001

    def __init__(self, view: QGraphicsView, parent=None):
        super().__init__(parent)

        if not isinstance(view, QGraphicsView):
            raise TypeError("Invalid map view.")

        self.view = view

        self._create_viewport_update_timer()
        self._connect_scrollbars()

    @property
    def zoom_level(self) -> float:
        view_transform = self.view.transform()

        return math.hypot(view_transform.m11(), view_transform.m12())

    def set_zoom_level(self, zoom_level: float):
        target_zoom = self._clamp_zoom(zoom_level)

        current_zoom = self.zoom_level

        if current_zoom <= 0.0:
            raise ValueError("Invalid current zoom factor.")

        scale_factor = target_zoom / current_zoom

        if self._is_neutral_scale(scale_factor):
            return

        self._scale_at_view_position(
            scale_factor=scale_factor, view_position=(self.view.viewport().rect().center())
        )

        self.notify_transform_changed()

    def zoom_by_wheel_delta(self, wheel_delta: int, view_position: QPoint) -> bool:
        wheel_delta = int(wheel_delta)

        if wheel_delta == 0:
            return False

        if not isinstance(view_position, QPoint):
            raise TypeError("Invalid view position.")

        current_zoom = self.zoom_level

        if current_zoom <= 0.0:
            return False

        if wheel_delta > 0:
            requested_factor = self.ZOOM_FACTOR

        else:
            requested_factor = 1.0 / self.ZOOM_FACTOR

        target_zoom = self._clamp_zoom(current_zoom * requested_factor)

        scale_factor = target_zoom / current_zoom

        if self._is_neutral_scale(scale_factor):
            return True

        self._scale_at_view_position(scale_factor=scale_factor, view_position=view_position)

        self.notify_transform_changed()

        return True

    def get_visible_scene_rect(self) -> QRectF:
        return self.view.mapToScene(self.view.viewport().rect()).boundingRect()

    def notify_transform_changed(self):
        self.zoom_changed.emit(self.zoom_level)

        self.schedule_viewport_update()

    def schedule_viewport_update(self, *args):
        self._viewport_update_timer.start()

    def emit_visible_scene_rect(self):
        self.visible_scene_rect_changed.emit(self.get_visible_scene_rect())

    def _create_viewport_update_timer(self):
        self._viewport_update_timer = QTimer(self)

        self._viewport_update_timer.setSingleShot(True)

        self._viewport_update_timer.setInterval(self.VIEWPORT_UPDATE_DELAY_MS)

        self._viewport_update_timer.timeout.connect(self.emit_visible_scene_rect)

    def _connect_scrollbars(self):
        self.view.horizontalScrollBar().valueChanged.connect(self.schedule_viewport_update)

        self.view.verticalScrollBar().valueChanged.connect(self.schedule_viewport_update)

    def _clamp_zoom(self, zoom_level: float) -> float:
        zoom_level = float(zoom_level)

        return max(self.MIN_ZOOM, min(zoom_level, self.MAX_ZOOM))

    def _is_neutral_scale(self, scale_factor: float) -> bool:
        return abs(scale_factor - 1.0) < self.ZOOM_COMPARISON_TOLERANCE

    def _scale_at_view_position(self, scale_factor: float, view_position: QPoint):
        scene_position_before = self.view.mapToScene(view_position)

        self.view.scale(scale_factor, scale_factor)

        scene_position_after = self.view.mapToScene(view_position)

        scene_delta = scene_position_after - scene_position_before

        self.view.translate(scene_delta.x(), scene_delta.y())
