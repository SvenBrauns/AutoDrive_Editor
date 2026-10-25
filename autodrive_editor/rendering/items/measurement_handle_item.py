from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QGraphicsItem, QGraphicsObject, QStyleOptionGraphicsItem, QWidget


class MeasurementHandleItem(QGraphicsObject):
    HANDLE_DIAMETER = 18.0
    HANDLE_RADIUS = HANDLE_DIAMETER / 2.0

    CROSS_SIZE = 5.0

    START_COLOR = QColor(30, 170, 255, 230)

    END_COLOR = QColor(255, 170, 30, 230)

    BORDER_COLOR = QColor(255, 255, 255, 255)

    TEXT_COLOR = QColor(255, 255, 255, 255)

    Z_VALUE = 500.0

    def __init__(self, point_index: int, label: str, movable: bool, parent=None):
        super().__init__(parent)

        if point_index not in (0, 1):
            raise ValueError("Der Messpunktindex muss 0 oder 1 sein.")

        label = str(label).strip()

        if not label:
            raise ValueError("Die Messpunktbezeichnung darf nicht leer sein.")

        self.point_index = point_index
        self.label = label
        self._movable = bool(movable)

        self.setZValue(self.Z_VALUE)

        self.setFlag(QGraphicsItem.ItemIgnoresTransformations, True)

        self.setAcceptedMouseButtons(Qt.NoButton)

        self.setCursor(Qt.SizeAllCursor if self._movable else Qt.ArrowCursor)

        self._border_pen = QPen(self.BORDER_COLOR)

        self._border_pen.setWidthF(1.5)

        self._fill_brush = QBrush(self._get_point_color())

        self._text_font = QFont()

        self._text_font.setBold(True)

        self._text_font.setPixelSize(10)

    @property
    def is_movable(self) -> bool:
        return self._movable

    def boundingRect(self) -> QRectF:
        margin = 2.0

        return QRectF(
            -self.HANDLE_RADIUS - margin,
            -self.HANDLE_RADIUS - margin,
            self.HANDLE_DIAMETER + margin * 2.0,
            self.HANDLE_DIAMETER + margin * 2.0,
        )

    def shape(self) -> QPainterPath:
        shape_path = QPainterPath()

        shape_path.addEllipse(
            QRectF(
                -self.HANDLE_RADIUS, -self.HANDLE_RADIUS, self.HANDLE_DIAMETER, self.HANDLE_DIAMETER
            )
        )

        return shape_path

    def paint(
        self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget | None = None
    ):
        painter.save()

        painter.setRenderHint(QPainter.Antialiasing, True)

        painter.setPen(self._border_pen)

        painter.setBrush(self._fill_brush)

        painter.drawEllipse(
            QRectF(
                -self.HANDLE_RADIUS, -self.HANDLE_RADIUS, self.HANDLE_DIAMETER, self.HANDLE_DIAMETER
            )
        )

        painter.setPen(self.BORDER_COLOR)

        painter.drawLine(-self.CROSS_SIZE, 0.0, self.CROSS_SIZE, 0.0)

        painter.drawLine(0.0, -self.CROSS_SIZE, 0.0, self.CROSS_SIZE)

        painter.setPen(self.TEXT_COLOR)

        painter.setFont(self._text_font)

        painter.drawText(self.boundingRect(), Qt.AlignCenter, self.label)

        painter.restore()

    def set_scene_position(self, scene_position):
        self.setPos(scene_position)

    def set_movable(self, movable: bool):
        movable = bool(movable)

        if movable == self._movable:
            return

        self._movable = movable

        self.setCursor(Qt.SizeAllCursor if self._movable else Qt.ArrowCursor)

        self.update()

    def _get_point_color(self) -> QColor:
        if self.point_index == 0:
            return QColor(self.START_COLOR)

        return QColor(self.END_COLOR)
