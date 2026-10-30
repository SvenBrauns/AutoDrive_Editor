from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QColor, QPainter, QPen, QPolygonF, QTransform

from autodrive_editor.file_io.savegame_stations import Stop
from autodrive_editor.rendering.display_style import DisplayStyle
from autodrive_editor.rendering.layers.map_layer_item import BOUNDS_MARGIN, MapLayerItem
from autodrive_editor.rendering.screen_size import screen_size, view_scale

# Arrow pointing up, 1 long, centred on the stop: tip, right corner, notch, left corner.
ARROW = QPolygonF([QPointF(0, -0.5), QPointF(0.35, 0.5), QPointF(0, 0.25), QPointF(-0.35, 0.5)])


class StationLayerItem(MapLayerItem):
    """An arrow at each stop of the stations in the savegame, along its lane, below the network."""

    def __init__(self, display_style: DisplayStyle):
        super().__init__(display_style, display_style.station_z)

        self.stops: list[Stop] = []
        self.headings: dict[Stop, float] = {}

    def set_stops(self, stops: list[Stop], headings: dict[Stop, float] | None = None):
        """headings: the arrow angle by stop, if not the stop's own heading."""

        self.prepareGeometryChange()

        self.stops = list(stops)
        self.headings = dict(headings or {})
        self.bounds = QRectF()

        if self.stops:
            xs = [stop.position[0] for stop in self.stops]
            zs = [stop.position[2] for stop in self.stops]
            bounds = QRectF(QPointF(min(xs), min(zs)), QPointF(max(xs), max(zs)))
            # Room for the arrows, which keep a minimum size on screen.
            self.bounds = bounds.adjusted(
                -BOUNDS_MARGIN, -BOUNDS_MARGIN, BOUNDS_MARGIN, BOUNDS_MARGIN
            )

        self.update()

    def set_network_bounds(self, network_bounds: QRectF):
        """The layer covers the stops, which may lie outside the network."""

    def paint(self, painter: QPainter, option, widget=None):
        scale = view_scale(painter)

        if not self.stops or not self.visibility.stations or scale <= 0:
            return

        style = self.display_style
        length = (
            screen_size(
                style.stop_arrow_length, scale, style.stop_arrow_min_px, style.stop_arrow_max_px
            )
            / scale
        )
        pen = QPen(QColor(*style.stop_outline_color), style.stop_outline_px)
        pen.setCosmetic(True)

        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setPen(pen)
        painter.setBrush(QColor(*style.stop_color))

        exposed = option.exposedRect.adjusted(-length, -length, length, length)

        for stop in self.stops:
            x, _, z = stop.position

            if not exposed.contains(x, z):
                continue

            transform = (
                QTransform()
                .translate(x, z)
                .rotate(self.headings.get(stop, stop.heading))
                .scale(length, length)
            )
            painter.drawPolygon(transform.map(ARROW))
