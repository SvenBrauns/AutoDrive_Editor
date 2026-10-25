from PySide6.QtCore import (
    QObject,
    QPoint,
    QRect,
    Signal
)
from PySide6.QtGui import QPainterPath
from PySide6.QtWidgets import (
    QApplication,
    QGraphicsView,
    QRubberBand
)


class ViewSelectionController(QObject):

    area_requested = Signal(
        object,
        object
    )

    area_preview_requested = Signal(
        object,
        object
    )

    area_preview_cleared = Signal()

    def __init__(
        self,
        view: QGraphicsView,
        parent=None
    ):
        super().__init__(
            parent
        )

        if not isinstance(
            view,
            QGraphicsView
        ):
            raise TypeError(
                "Die Kartenansicht ist ungültig."
            )

        self.view = view

        self._drag_active = False

        self._press_position = QPoint()
        self._current_position = QPoint()

        self._rubber_band = QRubberBand(
            QRubberBand.Rectangle,
            self.view.viewport()
        )

        self._rubber_band.hide()

    @property
    def drag_active(self) -> bool:
        return self._drag_active

    def begin(
        self,
        press_position: QPoint
    ):
        if not isinstance(
            press_position,
            QPoint
        ):
            raise TypeError(
                "Die Startposition der "
                "Bereichsauswahl ist ungültig."
            )

        self.cancel(
            emit_preview_cleared=False
        )

        self._press_position = QPoint(
            press_position
        )

        self._current_position = QPoint(
            press_position
        )

    def handle_drag(
        self,
        current_position: QPoint,
        modifiers
    ) -> bool:
        if not isinstance(
            current_position,
            QPoint
        ):
            raise TypeError(
                "Die aktuelle Position der "
                "Bereichsauswahl ist ungültig."
            )

        self._current_position = QPoint(
            current_position
        )

        if not self._drag_active:
            if not self._drag_threshold_reached():
                return False

            self._drag_active = True

            self._rubber_band.show()

        self._update_rubber_band()

        selection_path = (
            self._create_selection_path()
        )

        if selection_path is not None:
            self.area_preview_requested.emit(
                selection_path,
                modifiers
            )

        return True

    def finish(
        self,
        modifiers
    ):
        if not self._drag_active:
            self.cancel()
            return

        selection_path = (
            self._create_selection_path()
        )

        self._rubber_band.hide()

        self._drag_active = False

        if selection_path is not None:
            self.area_requested.emit(
                selection_path,
                modifiers
            )

        self.area_preview_cleared.emit()

        self._reset_positions()

    def cancel(
        self,
        emit_preview_cleared: bool = True
    ):
        had_active_preview = (
            self._drag_active
            or self._rubber_band.isVisible()
        )

        self._rubber_band.hide()

        self._drag_active = False

        self._reset_positions()

        if (
            emit_preview_cleared
            and had_active_preview
        ):
            self.area_preview_cleared.emit()

    def _drag_threshold_reached(self) -> bool:
        drag_distance = (
            self._current_position
            - self._press_position
        ).manhattanLength()

        return (
            drag_distance
            >= QApplication.startDragDistance()
        )

    def _update_rubber_band(self):
        selection_rect = QRect(
            self._press_position,
            self._current_position
        ).normalized()

        self._rubber_band.setGeometry(
            selection_rect
        )

    def _create_selection_path(
        self
    ) -> QPainterPath | None:
        selection_rect = (
            self._rubber_band.geometry()
        )

        if (
            selection_rect.width() <= 0
            or selection_rect.height() <= 0
        ):
            return None

        scene_polygon = self.view.mapToScene(
            selection_rect
        )

        selection_path = QPainterPath()

        selection_path.addPolygon(
            scene_polygon
        )

        selection_path.closeSubpath()

        return selection_path

    def _reset_positions(self):
        self._press_position = QPoint()
        self._current_position = QPoint()
