from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QColor, QPainter, QPen, QPolygonF

from autodrive_editor.file_io.savegame_sheds import IndoorArea
from autodrive_editor.rendering.display_style import DisplayStyle
from autodrive_editor.rendering.layers.map_layer_item import MapLayerItem


class ShedLayerItem(MapLayerItem):
    """Outlines of the indoor areas of the buildings in the savegame, below the network."""

    def __init__(self, display_style: DisplayStyle):
        super().__init__(display_style, display_style.shed_z)

        self.polygons: list[QPolygonF] = []

    def set_areas(self, areas: list[IndoorArea]):
        self.prepareGeometryChange()

        self.polygons = [QPolygonF([QPointF(x, z) for x, z in area.corners]) for area in areas]
        bounds = QRectF()

        for polygon in self.polygons:
            bounds = bounds.united(polygon.boundingRect())

        # Room for the outline, which is drawn at a fixed width on screen.
        self.bounds = bounds.adjusted(-1, -1, 1, 1) if self.polygons else QRectF()

        self.update()

    def set_network_bounds(self, network_bounds: QRectF):
        """The layer covers the sheds, which may lie outside the network."""

    def paint(self, painter: QPainter, option, widget=None):
        if not self.polygons or not self.visibility.sheds:
            return

        style = self.display_style
        pen = QPen(QColor(*style.shed_color), style.shed_outline_px)
        pen.setCosmetic(True)

        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setPen(pen)
        painter.setBrush(QColor(*style.shed_color, style.shed_fill_alpha))

        exposed = option.exposedRect

        for polygon in self.polygons:
            if polygon.boundingRect().intersects(exposed):
                painter.drawPolygon(polygon)
