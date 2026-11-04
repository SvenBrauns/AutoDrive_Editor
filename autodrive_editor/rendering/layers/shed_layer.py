from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QColor, QPainter, QPen, QPolygonF

from autodrive_editor.file_io.savegame_sheds import IndoorArea
from autodrive_editor.rendering.display_style import DisplayStyle
from autodrive_editor.rendering.layers.map_layer_item import MapLayerItem


class ShedLayerItem(MapLayerItem):
    """Outlines of the indoor areas of the buildings in the savegame, below the network; with
    silos=True the inner areas of the bunker silos, in their own colour. Picked areas are filled
    stronger."""

    def __init__(self, display_style: DisplayStyle, silos: bool = False):
        super().__init__(display_style, display_style.shed_z)

        self.silos = silos
        self.polygons: list[QPolygonF] = []
        self.picked: list[QPolygonF] = []

    def set_areas(self, areas: list[IndoorArea]):
        self.prepareGeometryChange()

        self.polygons = [QPolygonF([QPointF(x, z) for x, z in area.corners]) for area in areas]
        bounds = QRectF()

        for polygon in self.polygons:
            bounds = bounds.united(polygon.boundingRect())

        # Room for the outline, which is drawn at a fixed width on screen.
        self.bounds = bounds.adjusted(-1, -1, 1, 1) if self.polygons else QRectF()

        self.update()

    def set_picked(self, areas: list[IndoorArea]):
        self.picked = [QPolygonF([QPointF(x, z) for x, z in area.corners]) for area in areas]
        self.update()

    def set_network_bounds(self, network_bounds: QRectF):
        """The layer covers the sheds, which may lie outside the network."""

    def paint(self, painter: QPainter, option, widget=None):
        shown = self.visibility.silos if self.silos else self.visibility.sheds

        if not self.polygons or not shown:
            return

        style = self.display_style
        color = style.silo_color if self.silos else style.shed_color
        pen = QPen(QColor(*color), style.shed_outline_px)
        pen.setCosmetic(True)

        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setPen(pen)

        exposed = option.exposedRect

        for polygons, alpha in ((self.polygons, style.shed_fill_alpha), (self.picked, 160)):
            painter.setBrush(QColor(*color, alpha))

            for polygon in polygons:
                if polygon.boundingRect().intersects(exposed):
                    painter.drawPolygon(polygon)
