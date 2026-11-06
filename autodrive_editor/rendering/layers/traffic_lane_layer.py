from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QColor, QPainter, QPen, QPolygonF

from autodrive_editor.file_io.traffic_splines import TrafficLane
from autodrive_editor.rendering.display_style import DisplayStyle
from autodrive_editor.rendering.layers.map_layer_item import MapLayerItem


class TrafficLaneLayerItem(MapLayerItem):
    """The traffic lanes of the map as thin lines below the network, while the Roads task of the
    Generate tool is active."""

    def __init__(self, display_style: DisplayStyle):
        super().__init__(display_style, display_style.traffic_lane_z)

        self.lines: list[QPolygonF] = []

    def set_lanes(self, lanes: list[TrafficLane]):
        self.prepareGeometryChange()

        self.lines = [QPolygonF([QPointF(x, z) for x, _, z in lane.points]) for lane in lanes]
        bounds = QRectF()

        for line in self.lines:
            bounds = bounds.united(line.boundingRect())

        # Room for the line width, which is fixed on screen.
        self.bounds = bounds.adjusted(-1, -1, 1, 1) if self.lines else QRectF()

        self.update()

    def set_network_bounds(self, network_bounds: QRectF):
        """The layer covers the lanes, which may lie outside the network."""

    def paint(self, painter: QPainter, option, widget=None):
        if not self.lines:
            return

        style = self.display_style
        pen = QPen(
            QColor(*style.traffic_lane_color, style.traffic_lane_alpha), style.traffic_lane_px
        )
        pen.setCosmetic(True)

        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setPen(pen)

        exposed = option.exposedRect

        for line in self.lines:
            if line.boundingRect().intersects(exposed):
                painter.drawPolyline(line)
