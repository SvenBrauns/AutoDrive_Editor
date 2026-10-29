from PySide6.QtCore import QPointF
from PySide6.QtGui import QColor, QPainter, QPolygonF

from autodrive_editor.rendering.display_style import DisplayStyle
from autodrive_editor.rendering.layers.map_layer_item import MapLayerItem
from autodrive_editor.rendering.layers.node_layer import draw_points, node_diameter_px
from autodrive_editor.rendering.screen_size import view_scale

# Halo diameter as a multiple of the node diameter.
HALO_FACTOR = 2.2


class PlanLayerItem(MapLayerItem):
    """A colored halo behind the nodes the open plan changed. Drawn at every zoom level and at
    least plan_halo_min_px big, so the plan stays visible when zoomed out."""

    def __init__(self, display_style: DisplayStyle):
        super().__init__(display_style, display_style.plan_z)

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

        diameter_px = max(node_diameter_px(style, scale) * HALO_FACTOR, style.plan_halo_min_px)

        painter.setRenderHint(QPainter.Antialiasing, True)
        draw_points(painter, [self.points], QColor(*style.plan_color), diameter_px)
