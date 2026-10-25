from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QFontMetricsF, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QGraphicsItem, QGraphicsObject, QStyleOptionGraphicsItem, QWidget


class MeasurementResultItem(QGraphicsObject):
    HORIZONTAL_PADDING = 8.0
    VERTICAL_PADDING = 4.0

    BACKGROUND_COLOR = QColor(20, 20, 20, 220)

    BORDER_COLOR = QColor(255, 255, 255, 230)

    TEXT_COLOR = QColor(255, 255, 255, 255)

    Z_VALUE = 510.0

    def __init__(self, parent=None):
        super().__init__(parent)

        self._text = ""

        self._font = QFont()

        self._font.setBold(True)

        self._font.setPixelSize(12)

        self._bounding_rect = QRectF()

        self._background_brush = QBrush(self.BACKGROUND_COLOR)

        self._border_pen = QPen(self.BORDER_COLOR)

        self._border_pen.setWidthF(1.0)

        self.setZValue(self.Z_VALUE)

        self.setFlag(QGraphicsItem.ItemIgnoresTransformations, True)

        self.setAcceptedMouseButtons(Qt.NoButton)

        self.setVisible(False)

    @property
    def text(self) -> str:
        return self._text

    def boundingRect(self) -> QRectF:
        return QRectF(self._bounding_rect)

    def shape(self) -> QPainterPath:
        shape_path = QPainterPath()

        shape_path.addRoundedRect(self._bounding_rect, 4.0, 4.0)

        return shape_path

    def paint(
        self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget | None = None
    ):
        if not self.isVisible() or not self._text:
            return

        painter.save()

        painter.setRenderHint(QPainter.Antialiasing, True)

        painter.setPen(self._border_pen)

        painter.setBrush(self._background_brush)

        painter.drawRoundedRect(self._bounding_rect, 4.0, 4.0)

        painter.setPen(self.TEXT_COLOR)

        painter.setFont(self._font)

        painter.drawText(self._bounding_rect, Qt.AlignCenter, self._text)

        painter.restore()

    def set_text(self, text: str):
        text = str(text).strip()

        if text == self._text:
            return

        self.prepareGeometryChange()

        self._text = text

        if not self._text:
            self._bounding_rect = QRectF()

            self.setVisible(False)

            self.update()
            return

        font_metrics = QFontMetricsF(self._font)

        text_rect = font_metrics.boundingRect(self._text)

        width = text_rect.width() + self.HORIZONTAL_PADDING * 2.0

        height = text_rect.height() + self.VERTICAL_PADDING * 2.0

        self._bounding_rect = QRectF(-width / 2.0, -height / 2.0, width, height)

        self.setVisible(True)

        self.update()

    def clear(self):
        self.set_text("")
