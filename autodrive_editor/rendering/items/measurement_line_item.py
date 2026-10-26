from PySide6.QtCore import QLineF, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QGraphicsItem, QStyleOptionGraphicsItem, QWidget


class MeasurementLineItem(QGraphicsItem):
    """The line between the two measurement points."""

    LINE_COLOR = QColor(255, 255, 0, 230)

    LINE_WIDTH = 2.0

    Z_VALUE = 490.0

    BOUNDING_MARGIN = 8.0

    def __init__(self, parent=None):
        super().__init__(parent)

        self._start_position = QPointF()
        self._end_position = QPointF()

        self._line_pen = QPen(self.LINE_COLOR)

        self._line_pen.setWidthF(self.LINE_WIDTH)

        self._line_pen.setCosmetic(True)

        self._line_pen.setStyle(Qt.DashLine)

        self.setZValue(self.Z_VALUE)

        self.setAcceptedMouseButtons(Qt.NoButton)

        self.setVisible(False)

    @property
    def start_position(self) -> QPointF:
        return QPointF(self._start_position)

    @property
    def end_position(self) -> QPointF:
        return QPointF(self._end_position)

    def boundingRect(self) -> QRectF:
        line_rect = QRectF(self._start_position, self._end_position).normalized()

        return line_rect.adjusted(
            -self.BOUNDING_MARGIN, -self.BOUNDING_MARGIN, self.BOUNDING_MARGIN, self.BOUNDING_MARGIN
        )

    def paint(
        self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget | None = None
    ):
        if not self.isVisible():
            return

        painter.save()

        painter.setRenderHint(QPainter.Antialiasing, True)

        painter.setPen(self._line_pen)

        painter.drawLine(QLineF(self._start_position, self._end_position))

        painter.restore()

    def set_points(self, start_position: QPointF, end_position: QPointF):
        if not isinstance(start_position, QPointF):
            raise TypeError("Invalid start position of the measuring line.")

        if not isinstance(end_position, QPointF):
            raise TypeError("Invalid end position of the measuring line.")

        self.prepareGeometryChange()

        self._start_position = QPointF(start_position)

        self._end_position = QPointF(end_position)

        self.setVisible(True)

        self.update()

    def clear(self):
        self.prepareGeometryChange()

        self._start_position = QPointF()
        self._end_position = QPointF()

        self.setVisible(False)

        self.update()
