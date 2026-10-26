from PySide6.QtCore import QObject, QPoint, QRect, Qt, Signal
from PySide6.QtGui import QColor, QPainterPath, QPen, QPolygonF
from PySide6.QtWidgets import QApplication, QGraphicsPathItem, QGraphicsView, QRubberBand


class AreaSelectionController(QObject):
    """Draws the box (or a freehand lasso) while right dragging and reports the selected area
    as a scene path, so selection also works with a rotated view.
    """

    LASSO_COLOR = QColor(51, 153, 255)
    LASSO_Z_VALUE = 10_000.0

    area_requested = Signal(object, object)

    area_preview_requested = Signal(object, object)

    area_preview_cleared = Signal()

    def __init__(self, view: QGraphicsView, parent=None):
        super().__init__(parent)

        if not isinstance(view, QGraphicsView):
            raise TypeError("Invalid map view.")

        self.view = view

        self._drag_active = False

        self._press_position = QPoint()
        self._current_position = QPoint()

        self._rubber_band = QRubberBand(QRubberBand.Rectangle, self.view.viewport())

        self._rubber_band.hide()

        self._lasso = False
        self._lasso_points: list[QPoint] = []
        self._lasso_item: QGraphicsPathItem | None = None

    @property
    def drag_active(self) -> bool:
        return self._drag_active

    def begin(self, press_position: QPoint, lasso: bool = False):
        """Starts a box, or a freehand lasso that follows the mouse."""

        if not isinstance(press_position, QPoint):
            raise TypeError("Invalid start position of the area selection.")

        self.cancel(emit_preview_cleared=False)

        self._press_position = QPoint(press_position)

        self._current_position = QPoint(press_position)

        self._lasso = lasso
        self._lasso_points = [QPoint(press_position)]

    def handle_drag(self, current_position: QPoint, modifiers) -> bool:
        if not isinstance(current_position, QPoint):
            raise TypeError("Invalid current position of the area selection.")

        self._current_position = QPoint(current_position)

        if self._lasso:
            self._lasso_points.append(QPoint(current_position))

        if not self._drag_active:
            if not self._drag_threshold_reached():
                return False

            self._drag_active = True

            if not self._lasso:
                self._rubber_band.show()

        if self._lasso:
            self._update_lasso_item()
        else:
            self._update_rubber_band()

        selection_path = self._create_selection_path()

        if selection_path is not None:
            self.area_preview_requested.emit(selection_path, modifiers)

        return True

    def finish(self, modifiers):
        if not self._drag_active:
            self.cancel()
            return

        selection_path = self._create_selection_path()

        self._rubber_band.hide()
        self._remove_lasso_item()

        self._drag_active = False

        if selection_path is not None:
            self.area_requested.emit(selection_path, modifiers)

        self.area_preview_cleared.emit()

        self._reset_positions()

    def cancel(self, emit_preview_cleared: bool = True):
        had_active_preview = self._drag_active or self._rubber_band.isVisible()

        self._rubber_band.hide()
        self._remove_lasso_item()

        self._drag_active = False

        self._reset_positions()

        if emit_preview_cleared and had_active_preview:
            self.area_preview_cleared.emit()

    def _drag_threshold_reached(self) -> bool:
        drag_distance = (self._current_position - self._press_position).manhattanLength()

        return drag_distance >= QApplication.startDragDistance()

    def _update_rubber_band(self):
        selection_rect = QRect(self._press_position, self._current_position).normalized()

        self._rubber_band.setGeometry(selection_rect)

    def _lasso_scene_polygon(self) -> QPolygonF:
        return QPolygonF([self.view.mapToScene(point) for point in self._lasso_points])

    def _update_lasso_item(self):
        if self._lasso_item is None:
            pen = QPen(self.LASSO_COLOR)
            pen.setCosmetic(True)
            pen.setWidthF(1.5)
            pen.setStyle(Qt.DashLine)

            self._lasso_item = QGraphicsPathItem()
            self._lasso_item.setPen(pen)
            self._lasso_item.setZValue(self.LASSO_Z_VALUE)
            self.view.scene().addItem(self._lasso_item)

        path = QPainterPath()
        path.addPolygon(self._lasso_scene_polygon())
        path.closeSubpath()

        self._lasso_item.setPath(path)

    def _remove_lasso_item(self):
        if self._lasso_item is not None and self._lasso_item.scene() is not None:
            self._lasso_item.scene().removeItem(self._lasso_item)

        self._lasso_item = None

    def _create_selection_path(self) -> QPainterPath | None:
        if self._lasso:
            if len(self._lasso_points) < 3:
                return None

            selection_path = QPainterPath()
            selection_path.addPolygon(self._lasso_scene_polygon())
            selection_path.closeSubpath()

            return selection_path

        selection_rect = self._rubber_band.geometry()

        if selection_rect.width() <= 0 or selection_rect.height() <= 0:
            return None

        scene_polygon = self.view.mapToScene(selection_rect)

        selection_path = QPainterPath()

        selection_path.addPolygon(scene_polygon)

        selection_path.closeSubpath()

        return selection_path

    def _reset_positions(self):
        self._press_position = QPoint()
        self._current_position = QPoint()
        self._lasso_points = []
