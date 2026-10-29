import math

from PySide6.QtCore import QPointF
from PySide6.QtGui import QColor, QPen, QPolygonF

from autodrive_editor.model.connections import ConnectionType

MARKER_COLOR = QColor(30, 80, 160)


def paint_connection(painter, start, end, connection_type, style, arrow_px=7):
    colors = {
        ConnectionType.REGULAR: style.regular_connection_color,
        ConnectionType.DUAL: style.dual_connection_color,
        ConnectionType.REVERSE: style.reverse_connection_color,
    }
    color = QColor(*colors[connection_type])
    painter.setPen(QPen(color, 1.5))
    painter.drawLine(start, end)

    if connection_type != ConnectionType.DUAL:
        painter.setBrush(color)
        painter.drawPolygon(arrow_head(start, end, arrow_px))


def arrow_head(start: QPointF, end: QPointF, size: float) -> QPolygonF:
    """Arrow head in the middle of a line, pointing to its end."""

    dx, dy = end.x() - start.x(), end.y() - start.y()
    length = math.hypot(dx, dy)

    if length == 0:
        return QPolygonF()

    ux, uy = dx / length, dy / length
    middle = QPointF((start.x() + end.x()) / 2, (start.y() + end.y()) / 2)
    tip = middle + QPointF(ux, uy) * size / 2
    back = middle - QPointF(ux, uy) * size / 2
    side = QPointF(-uy, ux) * size / 2

    return QPolygonF([tip, back + side, back - side])
