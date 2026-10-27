from PySide6.QtCore import QPointF
from PySide6.QtGui import QColor, QPainter, QPolygonF

from autodrive_editor.rendering.display_style import DisplayStyle
from autodrive_editor.rendering.layers.map_layer_item import MapLayerItem
from autodrive_editor.rendering.layers.node_layer import draw_nodes, draw_points, node_diameter_px
from autodrive_editor.rendering.screen_size import screen_size, view_scale

RING_COLOR = QColor(255, 255, 255)
OUTLINE_COLOR = QColor(0, 0, 0, 200)
RING_MIN_PX = 1.5
RING_MAX_PX = 3.0


def selected_node_diameter_px(display_style: DisplayStyle, scale: float) -> float:
    return max(node_diameter_px(display_style, scale), display_style.selected_node_min_px)


def selection_ring_px(display_style: DisplayStyle, scale: float) -> float:
    return screen_size(display_style.selected_node_ring_width, scale, RING_MIN_PX, RING_MAX_PX)


class SelectionLayerItem(MapLayerItem):
    """Selected nodes with a white ring. They are drawn at every zoom level and at least
    selected_node_min_px big, so a selection stays visible when zoomed out."""

    def __init__(self, display_style: DisplayStyle):
        super().__init__(display_style, display_style.selected_node_z)

        self.regular = QPolygonF()
        self.subprio = QPolygonF()

    @property
    def node_count(self) -> int:
        return self.regular.size() + self.subprio.size()

    def set_nodes(self, nodes):
        self.regular = QPolygonF()
        self.subprio = QPolygonF()

        for node in nodes:
            (self.subprio if node.is_subprio else self.regular).append(QPointF(node.x, node.z))

        self.update()

    def paint(self, painter: QPainter, option, widget=None):
        if self.node_count == 0 or not self.visibility.nodes:
            return

        style = self.display_style
        scale = view_scale(painter)

        if scale <= 0:
            return

        diameter_px = selected_node_diameter_px(style, scale)
        ring_px = selection_ring_px(style, scale)
        polygons = [self.regular, self.subprio]

        painter.setRenderHint(QPainter.Antialiasing, True)

        draw_points(painter, polygons, OUTLINE_COLOR, diameter_px + 2 * ring_px + 2)
        draw_points(painter, polygons, RING_COLOR, diameter_px + 2 * ring_px)
        draw_nodes(painter, [self.regular], [self.subprio], diameter_px, border_px=0)
