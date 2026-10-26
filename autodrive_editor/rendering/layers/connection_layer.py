from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QPolygonF

from autodrive_editor.model.connections import ConnectionType
from autodrive_editor.rendering.display_style import DisplayStyle
from autodrive_editor.rendering.layers.map_layer_item import MapLayerItem
from autodrive_editor.rendering.layers.network_tiles import NetworkTiles
from autodrive_editor.rendering.screen_size import screen_size, view_scale

# An arrow takes at most this share of its connection's length on screen.
ARROW_SHARE = 1 / 3
ARROW_WIDTH_RATIO = 0.8


class ConnectionLayerItem(MapLayerItem):
    """All connections as lines of the same on-screen width at every zoom level, with an arrow in
    the middle of each one-way connection that is long enough on screen to hold one."""

    def __init__(self, tiles: NetworkTiles, display_style: DisplayStyle):
        super().__init__(display_style, display_style.connection_z)

        self.tiles = tiles
        self.drawn_arrows = 0

    def _colors(self) -> dict[ConnectionType, QColor]:
        style = self.display_style

        return {
            ConnectionType.REGULAR: QColor(*style.regular_connection_color),
            ConnectionType.DUAL: QColor(*style.dual_connection_color),
            ConnectionType.REVERSE: QColor(*style.reverse_connection_color),
        }

    def paint(self, painter: QPainter, option, widget=None):
        self.tiles.refresh()

        style = self.display_style
        scale = view_scale(painter)

        if scale <= 0:
            return

        arrow_margin = style.arrow_max_px / scale
        exposed = option.exposedRect.adjusted(
            -arrow_margin, -arrow_margin, arrow_margin, arrow_margin
        )
        tiles = self.tiles.get_connection_tiles(exposed)
        colors = self._colors()

        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setBrush(Qt.NoBrush)

        width_px = screen_size(
            style.connection_width, scale, style.connection_min_px, style.connection_max_px
        )

        for connection_type, color in colors.items():
            pen = QPen(color, width_px)
            pen.setCosmetic(True)
            # Round caps make Qt stroke every segment slowly; nodes cover the joints anyway.
            pen.setCapStyle(Qt.FlatCap)
            painter.setPen(pen)

            for tile in tiles:
                path = tile.paths[connection_type]

                if not path.isEmpty():
                    painter.drawPath(path)

        arrow_paths = self._build_arrow_paths(tiles, exposed, scale)

        painter.setPen(Qt.NoPen)

        for connection_type, path in arrow_paths.items():
            if not path.isEmpty():
                painter.fillPath(path, colors[connection_type])

    def _build_arrow_paths(self, tiles, exposed, scale) -> dict[ConnectionType, QPainterPath]:
        style = self.display_style

        arrow_length = (
            screen_size(style.arrow_length, scale, style.arrow_min_px, style.arrow_max_px) / scale
        )
        shortest_arrow = style.arrow_min_px / scale
        # Connections shorter than this cannot hold an arrow of the minimum size.
        shortest_connection = shortest_arrow / ARROW_SHARE

        paths = {ConnectionType.REGULAR: QPainterPath(), ConnectionType.REVERSE: QPainterPath()}
        count = 0

        for tile in tiles:
            # Sorted longest first, so the loop stops at the first one that is too short.
            for length, source_x, source_z, target_x, target_z, connection_type in tile.one_way:
                if length < shortest_connection:
                    break

                middle_x = (source_x + target_x) / 2
                middle_z = (source_z + target_z) / 2

                if not exposed.contains(middle_x, middle_z):
                    continue

                size = min(arrow_length, length * ARROW_SHARE)
                direction_x = (target_x - source_x) / length
                direction_z = (target_z - source_z) / length
                half_width = size * ARROW_WIDTH_RATIO / 2

                tip_x = middle_x + direction_x * size / 2
                tip_z = middle_z + direction_z * size / 2
                base_x = middle_x - direction_x * size / 2
                base_z = middle_z - direction_z * size / 2

                paths[connection_type].addPolygon(
                    QPolygonF(
                        (
                            QPointF(tip_x, tip_z),
                            QPointF(
                                base_x - direction_z * half_width, base_z + direction_x * half_width
                            ),
                            QPointF(
                                base_x + direction_z * half_width, base_z - direction_x * half_width
                            ),
                        )
                    )
                )
                count += 1

        self.drawn_arrows = count

        return paths
