from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QPainter
from PySide6.QtSvgWidgets import QGraphicsSvgItem
from PySide6.QtWidgets import QGraphicsItem


class MarkerLabelItem(QGraphicsItem):
    """The marker name on a light background. It keeps its size on screen
    and stays upright when the map is zoomed or rotated."""

    PADDING_X = 4.0
    PADDING_Y = 1.0

    TEXT_COLOR = QColor(15, 45, 82)
    BACKGROUND_COLOR = QColor(255, 255, 255, 215)
    BORDER_COLOR = QColor(15, 45, 82, 140)

    def __init__(self, text: str, parent=None):
        super().__init__(parent)

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations)
        self.setAcceptedMouseButtons(Qt.MouseButton.NoButton)

        self.text = text
        self.font = QFont()
        self.font.setPointSizeF(8.5)

        metrics = QFontMetricsF(self.font)
        self._rect = QRectF(
            0,
            0,
            metrics.horizontalAdvance(text) + 2 * self.PADDING_X,
            metrics.height() + 2 * self.PADDING_Y,
        )

    def boundingRect(self) -> QRectF:
        return self._rect

    def paint(self, painter: QPainter, option, widget=None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(self.BORDER_COLOR)
        painter.setBrush(self.BACKGROUND_COLOR)
        painter.drawRoundedRect(self._rect.adjusted(0.5, 0.5, -0.5, -0.5), 3, 3)

        painter.setFont(self.font)
        painter.setPen(self.TEXT_COLOR)
        painter.drawText(self._rect, Qt.AlignmentFlag.AlignCenter, self.text)


class MarkerItem(QGraphicsSvgItem):
    """The marker icon shown above a node, optionally with its name."""

    def __init__(self, svg_path, name: str = "", show_name: bool = False):
        super().__init__(svg_path)

        self.setAcceptedMouseButtons(Qt.NoButton)

        self.label_item = MarkerLabelItem(name, self) if name else None

        if self.label_item is not None:
            # Right of the icon's upper part.
            bounds = self.boundingRect()
            self.label_item.setPos(bounds.right(), bounds.top() + bounds.height() * 0.1)
            self.label_item.setVisible(show_name)

    def set_name_visible(self, visible: bool):
        if self.label_item is not None:
            self.label_item.setVisible(visible)
