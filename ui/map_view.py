from PySide6.QtCore import Signal
from PySide6.QtWidgets import QGraphicsView


class MapView(QGraphicsView):

    zoom_changed = Signal(float)

    ZOOM_FACTOR = 1.15
    MIN_ZOOM = 0.02
    MAX_ZOOM = 50.0

    def __init__(self):
        super().__init__()

        self.setDragMode(
            QGraphicsView.ScrollHandDrag
        )

        self.setTransformationAnchor(
            QGraphicsView.AnchorUnderMouse
        )

        self.setResizeAnchor(
            QGraphicsView.AnchorViewCenter
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

        event.accept()

    def fitInView(self, *args):
        super().fitInView(
            *args
        )

        self.zoom_changed.emit(
            self.zoom_level
        )

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