import math
from dataclasses import dataclass, field

from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QPainterPath, QPolygonF

from autodrive_editor.model.connections import ConnectionType
from autodrive_editor.rendering.spatial.connection_index import ConnectionSpatialIndex
from autodrive_editor.rendering.spatial.node_index import NodeSpatialIndex


@dataclass
class ConnectionTile:
    """One path per connection type, plus the one-way connections that can get arrows as
    (length, source_x, source_z, target_x, target_z, type), longest first."""

    paths: dict[ConnectionType, QPainterPath]
    one_way: list[tuple[float, float, float, float, float, ConnectionType]]
    bounds: QRectF


@dataclass
class NodeTile:
    regular: QPolygonF = field(default_factory=QPolygonF)
    subprio: QPolygonF = field(default_factory=QPolygonF)


class NetworkTiles:
    """Drawing data of the network, split into the tiles of the spatial indexes. Qt draws a tile's
    paths and points in one call each, so even the whole map draws quickly. After edits, only the
    tiles the indexes report as changed are rebuilt, on the next refresh()."""

    def __init__(self, node_index: NodeSpatialIndex, connection_index: ConnectionSpatialIndex):
        self.node_index = node_index
        self.connection_index = connection_index

        self.connection_tiles: dict[tuple[int, int], ConnectionTile] = {}
        self.node_tiles: dict[tuple[int, int], NodeTile] = {}

    def clear(self):
        self.connection_tiles.clear()
        self.node_tiles.clear()

    def refresh(self):
        for tile_key in self.connection_index.take_changed_tiles():
            connections = self.connection_index.connections_by_drawing_tile.get(tile_key)

            if connections:
                self.connection_tiles[tile_key] = _build_connection_tile(connections.values())

            else:
                self.connection_tiles.pop(tile_key, None)

        for tile_key in self.node_index.take_changed_tiles():
            nodes = self.node_index.nodes_by_tile.get(tile_key)

            if nodes:
                self.node_tiles[tile_key] = _build_node_tile(nodes.values())

            else:
                self.node_tiles.pop(tile_key, None)

    def get_connection_tiles(self, rect: QRectF) -> list[ConnectionTile]:
        return [tile for tile in self.connection_tiles.values() if tile.bounds.intersects(rect)]

    def get_node_tiles(self, rect: QRectF) -> list[NodeTile]:
        size = self.node_index.tile_size

        return [
            tile
            for (tile_x, tile_z), tile in self.node_tiles.items()
            if QRectF(tile_x * size, tile_z * size, size, size).intersects(rect)
        ]


def _build_connection_tile(connections) -> ConnectionTile:
    paths = {connection_type: QPainterPath() for connection_type in ConnectionType}
    one_way = []

    for connection in connections:
        path = paths[connection.connection_type]
        path.moveTo(connection.source_x, connection.source_z)
        path.lineTo(connection.target_x, connection.target_z)

        if connection.connection_type != ConnectionType.DUAL:
            source_x, source_z = connection.source_x, connection.source_z
            target_x, target_z = connection.target_x, connection.target_z
            length = math.hypot(target_x - source_x, target_z - source_z)

            if length > 0:
                one_way.append(
                    (length, source_x, source_z, target_x, target_z, connection.connection_type)
                )

    one_way.sort(key=lambda entry: entry[0], reverse=True)

    bounds = QRectF()

    for path in paths.values():
        if not path.isEmpty():
            bounds = bounds.united(path.boundingRect())

    # Bounds of zero width or height (one straight line) never intersect, hence the margin.
    return ConnectionTile(paths=paths, one_way=one_way, bounds=bounds.adjusted(-1, -1, 1, 1))


def _build_node_tile(nodes) -> NodeTile:
    tile = NodeTile()

    for node in nodes:
        (tile.subprio if node.is_subprio else tile.regular).append(QPointF(node.x, node.z))

    return tile
