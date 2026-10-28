from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QPolygonF

from autodrive_editor.model.connections import ConnectionType
from autodrive_editor.rendering.display_style import DisplayStyle
from autodrive_editor.rendering.layers.map_layer_item import MapLayerItem
from autodrive_editor.rendering.layers.network_tiles import NetworkTiles
from autodrive_editor.rendering.screen_size import screen_size, view_scale

# An arrow takes at most this share of its connection's length on screen.
ARROW_SHARE = 1 / 3
# Each of a dual connection's two arrows takes at most this share, so they never touch.
DUAL_ARROW_SHARE = 1 / 4
ARROW_WIDTH_RATIO = 0.8


class ConnectionLayerItem(MapLayerItem):
    """All connections as lines of the same on-screen width at every zoom level, colored by type.
    Connections long enough on screen get arrows: one-way ones in the middle, dual ones a third
    from each end."""

    def __init__(self, tiles: NetworkTiles, display_style: DisplayStyle):
        super().__init__(display_style, display_style.connection_z)

        self.tiles = tiles
        self.drawn_arrows = 0

    def _colors(self) -> dict[ConnectionType, QColor]:
        """Colors of the shown connection types."""

        style = self.display_style
        colors = {
            ConnectionType.REGULAR: style.regular_connection_color,
            ConnectionType.DUAL: style.dual_connection_color,
            ConnectionType.REVERSE: style.reverse_connection_color,
        }

        return {
            connection_type: QColor(*color)
            for connection_type, color in colors.items()
            if self.visibility.shows_connection(connection_type)
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

        arrow_paths = self._build_arrow_paths(tiles, exposed, scale, colors.keys())

        painter.setPen(Qt.NoPen)

        for connection_type, path in arrow_paths.items():
            if not path.isEmpty():
                painter.fillPath(path, colors[connection_type])

    def _build_arrow_paths(
        self, tiles, exposed, scale, shown_types
    ) -> dict[ConnectionType, QPainterPath]:
        style = self.display_style

        arrow_length = (
            screen_size(style.arrow_length, scale, style.arrow_min_px, style.arrow_max_px) / scale
        )
        shortest_arrow = style.arrow_min_px / scale
        # Connections shorter than this cannot hold an arrow of the minimum size.
        shortest_connection = shortest_arrow / ARROW_SHARE

        paths = {connection_type: QPainterPath() for connection_type in shown_types}
        count = 0

        for tile in tiles:
            # Sorted longest first, so the loop stops at the first one that is too short.
            for length, source_x, source_z, target_x, target_z, connection_type in tile.arrows:
                if length < shortest_connection:
                    break

                if connection_type not in paths:
                    continue

                direction_x = (target_x - source_x) / length
                direction_z = (target_z - source_z) / length

                if connection_type == ConnectionType.DUAL:
                    size = min(arrow_length, length * DUAL_ARROW_SHARE)

                    if size < shortest_arrow:
                        continue

                    # One arrow a third from each end, pointing to that end.
                    arrows = (
                        (1 / 3, -direction_x, -direction_z),
                        (2 / 3, direction_x, direction_z),
                    )

                else:
                    size = min(arrow_length, length * ARROW_SHARE)
                    arrows = ((1 / 2, direction_x, direction_z),)

                for share, arrow_x, arrow_z in arrows:
                    center_x = source_x + (target_x - source_x) * share
                    center_z = source_z + (target_z - source_z) * share

                    if exposed.contains(center_x, center_z):
                        paths[connection_type].addPolygon(
                            _arrow(center_x, center_z, arrow_x, arrow_z, size)
                        )
                        count += 1

        self.drawn_arrows = count

        return paths


def _arrow(center_x, center_z, direction_x, direction_z, size) -> QPolygonF:
    """Triangle of the given length around the center, its tip in the given unit direction."""

    half_width = size * ARROW_WIDTH_RATIO / 2
    tip_x = center_x + direction_x * size / 2
    tip_z = center_z + direction_z * size / 2
    base_x = center_x - direction_x * size / 2
    base_z = center_z - direction_z * size / 2

    return QPolygonF(
        (
            QPointF(tip_x, tip_z),
            QPointF(base_x - direction_z * half_width, base_z + direction_x * half_width),
            QPointF(base_x + direction_z * half_width, base_z - direction_x * half_width),
        )
    )
