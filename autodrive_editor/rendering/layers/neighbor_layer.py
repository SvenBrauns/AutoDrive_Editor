from PySide6.QtCore import QPointF
from PySide6.QtGui import QColor, QPainter, QPolygonF

from autodrive_editor.rendering.display_style import DisplayStyle
from autodrive_editor.rendering.layers.map_layer_item import MapLayerItem
from autodrive_editor.rendering.layers.node_layer import NODE_BORDER_COLOR, draw_points
from autodrive_editor.rendering.layers.selection_layer import selected_node_diameter_px
from autodrive_editor.rendering.screen_size import view_scale


class NeighborLayerItem(MapLayerItem):
    """The nodes connected to the node under the pointer, in one color. Drawn above the
    selection at the size of selected nodes, so a selected neighbour keeps its ring."""

    def __init__(self, display_style: DisplayStyle):
        super().__init__(display_style, display_style.neighbor_node_z)

        self.points = QPolygonF()

    def set_nodes(self, nodes):
        self.points = QPolygonF([QPointF(node.x, node.z) for node in nodes])
        self.update()

    def paint(self, painter: QPainter, option, widget=None):
        if self.points.isEmpty() or not self.visibility.nodes:
            return

        style = self.display_style
        scale = view_scale(painter)

        if scale <= 0:
            return

        diameter_px = selected_node_diameter_px(style, scale)

        painter.setRenderHint(QPainter.Antialiasing, True)
        draw_points(painter, [self.points], NODE_BORDER_COLOR, diameter_px + 2)
        draw_points(painter, [self.points], QColor(*style.neighbor_node_color), diameter_px)
