"""The scale bar in the bottom-left corner of the map."""

import math

from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen

MAX_WIDTH_PX = 120
MARGIN_PX = 12
TICK_PX = 6
TEXT_PIXEL_SIZE = 12

# Light bar with a dark outline: readable on every background.
BAR_COLOR = QColor(255, 255, 255)
OUTLINE_COLOR = QColor(0, 0, 0, 180)


def scale_bar_metres(pixels_per_metre: float, max_pixels: float = MAX_WIDTH_PX) -> float:
    """The longest round length (1, 2 or 5 × 10ⁿ m) that fits into max_pixels."""

    longest = max_pixels / pixels_per_metre
    power = 10 ** math.floor(math.log10(longest))

    return next(step * power for step in (5, 2, 1) if step * power <= longest * (1 + 1e-9))


def scale_bar_text(metres: float) -> str:
    return f"{metres / 1000:g} km" if metres >= 1000 else f"{metres:g} m"


def draw_scale_bar(painter: QPainter, bottom_left: QPoint, pixels_per_metre: float):
    """Draws the bar with end ticks and its length above it. The painter is in pixels."""

    metres = scale_bar_metres(pixels_per_metre)
    width = metres * pixels_per_metre
    left = QPointF(bottom_left.x() + MARGIN_PX, bottom_left.y() - MARGIN_PX)

    bar = QPainterPath(left + QPointF(0, -TICK_PX))
    bar.lineTo(left)
    bar.lineTo(left + QPointF(width, 0))
    bar.lineTo(left + QPointF(width, -TICK_PX))

    font = painter.font()
    font.setPixelSize(TEXT_PIXEL_SIZE)
    text = QPainterPath()
    text.addText(left + QPointF(4, -TICK_PX), font, scale_bar_text(metres))

    painter.save()
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setBrush(Qt.NoBrush)
    painter.setPen(QPen(OUTLINE_COLOR, 4, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    painter.drawPath(bar)
    painter.drawPath(text)
    painter.setPen(QPen(BAR_COLOR, 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    painter.drawPath(bar)
    painter.setPen(Qt.NoPen)
    painter.setBrush(BAR_COLOR)
    painter.drawPath(text)
    painter.restore()
