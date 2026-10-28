"""Checks what the map view really draws, by painting it into an image."""

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QImage, QPainter

from autodrive_editor.rendering.display_style import DisplayStyle

RED = QColor(*DisplayStyle().regular_node_color).name()
ORANGE = QColor(*DisplayStyle().subprio_node_color).name()


def drawn_color(window, x, z) -> str:
    """Color name of the pixel drawn at the map position."""

    view = window.view
    image = view.viewport().grab().toImage()
    ratio = image.devicePixelRatio()
    point = view.mapFromScene(x, z)

    return image.pixelColor(round(point.x() * ratio), round(point.y() * ratio)).name()


def shown_marker_names(window) -> dict[int, str]:
    """Marker names drawn on the map, by node id."""

    window.view.viewport().grab()

    return dict(window.scene_renderer.marker_layer.shown_names)


def paint_scene(scene, center, scale, size=200):
    """Paints the scene around the map point center at scale (pixels per metre)."""

    image = QImage(size, size, QImage.Format_ARGB32_Premultiplied)
    image.fill(Qt.white)

    half = size / 2 / scale
    source = QRectF(center[0] - half, center[1] - half, 2 * half, 2 * half)

    painter = QPainter(image)
    scene.render(painter, QRectF(0, 0, size, size), source)
    painter.end()

    return PaintedScene(image, source, scale)


class PaintedScene:
    def __init__(self, image, source, scale):
        self.image = image
        self.source = source
        self.scale = scale

    def color_at(self, x, z) -> str:
        column = round((x - self.source.left()) * self.scale)
        row = round((z - self.source.top()) * self.scale)

        return self.image.pixelColor(column, row).name()
