import math
from collections import defaultdict

from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QPainterPath

from autodrive_editor.model.autodrive_data import AutoDriveData, NodeData


class NodeSpatialIndex:
    """Finds nodes in a map area quickly by sorting them into square tiles."""

    DEFAULT_TILE_SIZE = 256.0

    def __init__(self, tile_size=DEFAULT_TILE_SIZE):
        self.tile_size = self._validate_tile_size(tile_size)

        # Each tile maps node id -> NodeData, so single nodes can be
        # moved between tiles without scanning a whole tile.
        self.nodes_by_tile = defaultdict(dict)

        self._tile_key_by_node_id: dict[int, tuple[int, int]] = {}

        self.node_count = 0

    def clear(self):
        self.nodes_by_tile.clear()
        self._tile_key_by_node_id.clear()
        self.node_count = 0

    def build(self, autodrive_data: AutoDriveData):
        self.clear()

        for node_data in autodrive_data.get_sorted_nodes():
            self._insert_node(node_data)

        self.node_count = len(self._tile_key_by_node_id)

    def update_nodes(self, nodes):
        """Moves already indexed nodes to the tiles of their
        current positions."""

        for node_data in nodes:
            old_tile_key = self._tile_key_by_node_id.get(node_data.node_id)

            if old_tile_key is None:
                continue

            new_tile_key = self._get_tile_key(node_data.x, node_data.z)

            if new_tile_key == old_tile_key:
                continue

            old_tile = self.nodes_by_tile[old_tile_key]

            old_tile.pop(node_data.node_id, None)

            if not old_tile:
                del self.nodes_by_tile[old_tile_key]

            self._insert_node(node_data)

    def add_nodes(self, nodes):
        for node_data in nodes:
            self._insert_node(node_data)

        self.node_count = len(self._tile_key_by_node_id)

    def remove_nodes(self, node_ids):
        for node_id in node_ids:
            tile_key = self._tile_key_by_node_id.pop(node_id, None)

            if tile_key is None:
                continue

            tile = self.nodes_by_tile[tile_key]

            tile.pop(node_id, None)

            if not tile:
                del self.nodes_by_tile[tile_key]

        self.node_count = len(self._tile_key_by_node_id)

    def _insert_node(self, node_data: NodeData):
        tile_key = self._get_tile_key(node_data.x, node_data.z)

        self.nodes_by_tile[tile_key][node_data.node_id] = node_data

        self._tile_key_by_node_id[node_data.node_id] = tile_key

    def get_nodes_in_rect(self, visible_rect: QRectF, padding=0.0) -> list[NodeData]:
        padding = max(0.0, float(padding))

        query_rect = visible_rect.adjusted(-padding, -padding, padding, padding)

        if query_rect.isEmpty():
            return []

        minimum_tile_x = math.floor(query_rect.left() / self.tile_size)

        maximum_tile_x = math.floor(query_rect.right() / self.tile_size)

        minimum_tile_z = math.floor(query_rect.top() / self.tile_size)

        maximum_tile_z = math.floor(query_rect.bottom() / self.tile_size)

        visible_nodes = []

        for tile_x in range(minimum_tile_x, maximum_tile_x + 1):
            for tile_z in range(minimum_tile_z, maximum_tile_z + 1):
                tile_nodes = self.nodes_by_tile.get((tile_x, tile_z), {})

                for node_data in tile_nodes.values():
                    if not query_rect.contains(node_data.x, node_data.z):
                        continue

                    visible_nodes.append(node_data)

        return visible_nodes

    def get_nodes_in_path(self, selection_path: QPainterPath) -> list[NodeData]:
        if selection_path.isEmpty():
            return []

        path_bounds = selection_path.boundingRect()

        candidate_nodes = self.get_nodes_in_rect(path_bounds)

        return [
            node_data
            for node_data in candidate_nodes
            if selection_path.contains(QPointF(node_data.x, node_data.z))
        ]

    def _get_tile_key(self, x, z):
        return (math.floor(x / self.tile_size), math.floor(z / self.tile_size))

    @staticmethod
    def _validate_tile_size(tile_size):
        tile_size = float(tile_size)

        if tile_size <= 0:
            raise ValueError("Die Node-Kachelgröße muss größer als 0 sein.")

        return tile_size
