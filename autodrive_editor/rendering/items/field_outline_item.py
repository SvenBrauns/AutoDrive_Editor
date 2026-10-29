from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import QGraphicsItem

from autodrive_editor.file_io.ground_map import Field

OUTLINE_COLOR = QColor(255, 235, 120)
OUTLINE_PX = 1.5
LABEL_PX = 13


class FieldOutlineItem(QGraphicsItem):
    """Field outlines with their numbers, drawn over the ground map at a fixed width on screen."""

    # Above the background (-1000), below the grid (-900).
    Z_VALUE = -950.0

    def __init__(self, fields: list[Field]):
        super().__init__()

        self.setFlag(QGraphicsItem.ItemUsesExtendedStyleOption, True)
        self.setAcceptedMouseButtons(Qt.NoButton)
        self.setZValue(self.Z_VALUE)

        self.fields = [
            (field, QPolygonF([QPointF(x, z) for x, z in field.points])) for field in fields
        ]
        self.bounds = QRectF()

        for _, polygon in self.fields:
            self.bounds = self.bounds.united(polygon.boundingRect())

    def boundingRect(self) -> QRectF:
        return self.bounds

    def paint(self, painter: QPainter, option, widget=None):
        exposed = option.exposedRect
        shown = [
            (field, polygon)
            for field, polygon in self.fields
            if polygon.boundingRect().intersects(exposed)
        ]

        pen = QPen(OUTLINE_COLOR, OUTLINE_PX)
        pen.setCosmetic(True)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)

        for _, polygon in shown:
            painter.drawPolygon(polygon)

        # Numbers stay upright and the same size on screen at every zoom and rotation.
        transform = painter.worldTransform()
        font = QFont()
        font.setPixelSize(LABEL_PX)
        font.setBold(True)

        painter.save()
        painter.resetTransform()
        painter.setFont(font)

        for field, _ in shown:
            center = transform.map(QPointF(*field.label_position))
            painter.drawText(
                QRectF(center.x() - 30, center.y() - 10, 60, 20), Qt.AlignCenter, str(field.number)
            )

        painter.restore()
