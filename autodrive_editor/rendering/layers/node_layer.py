from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPen, QPolygonF

from autodrive_editor.rendering.display_style import DisplayStyle
from autodrive_editor.rendering.layers.map_layer_item import MapLayerItem
from autodrive_editor.rendering.layers.network_tiles import NetworkTiles
from autodrive_editor.rendering.screen_size import fade_in, view_scale

REGULAR_NODE_COLOR = QColor(230, 30, 30)
SUBPRIO_NODE_COLOR = QColor(255, 160, 0)
NODE_BORDER_COLOR = QColor(0, 0, 0)
MAX_BORDER_PX = 2.0


def node_diameter_px(display_style: DisplayStyle, scale: float) -> float:
    """Diameter of a node on screen: its map size, up to node_max_px."""

    return min(display_style.node_diameter * scale, display_style.node_max_px)


def node_opacity(display_style: DisplayStyle, scale: float) -> float:
    """Nodes fade in while they grow on screen; 0 means they are not drawn."""

    return fade_in(
        node_diameter_px(display_style, scale),
        display_style.node_fade_start_px,
        display_style.node_fade_end_px,
    )


def draw_points(painter: QPainter, polygons, color: QColor, diameter_px: float):
    """Round dots of the given screen diameter, one Qt call per polygon."""

    pen = QPen(color, diameter_px)
    pen.setCosmetic(True)
    pen.setCapStyle(Qt.RoundCap)
    painter.setPen(pen)

    for polygon in polygons:
        if not polygon.isEmpty():
            painter.drawPoints(polygon)


def draw_nodes(
    painter: QPainter,
    regular: list[QPolygonF],
    subprio: list[QPolygonF],
    diameter_px: float,
    border_px: float,
):
    if border_px > 0.05:
        draw_points(painter, regular + subprio, NODE_BORDER_COLOR, diameter_px + 2 * border_px)

    draw_points(painter, regular, REGULAR_NODE_COLOR, diameter_px)
    draw_points(painter, subprio, SUBPRIO_NODE_COLOR, diameter_px)


class NodeLayerItem(MapLayerItem):
    """All nodes as dots at their map size. They fade in while zooming in instead of appearing
    at a fixed zoom level, and stop growing at node_max_px."""

    def __init__(self, tiles: NetworkTiles, display_style: DisplayStyle):
        super().__init__(display_style, display_style.node_z)

        self.tiles = tiles

    def paint(self, painter: QPainter, option, widget=None):
        self.tiles.refresh()

        style = self.display_style
        scale = view_scale(painter)
        opacity = node_opacity(style, scale) if scale > 0 else 0.0

        if opacity <= 0:
            return

        diameter_px = node_diameter_px(style, scale)
        border_px = min(style.node_border_width * scale, MAX_BORDER_PX)
        margin = (diameter_px / 2 + border_px) / scale

        tiles = self.tiles.get_node_tiles(
            option.exposedRect.adjusted(-margin, -margin, margin, margin)
        )

        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setOpacity(painter.opacity() * opacity)

        draw_nodes(
            painter,
            [tile.regular for tile in tiles],
            [tile.subprio for tile in tiles],
            diameter_px,
            border_px,
        )
