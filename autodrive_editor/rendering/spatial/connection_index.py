import math
from collections import defaultdict

from PySide6.QtCore import QRectF

from autodrive_editor.model.autodrive_data import AutoDriveData
from autodrive_editor.model.connections import get_connection_type
from autodrive_editor.rendering.connections.connection_data import ConnectionData


class ConnectionSpatialIndex:
    """Finds connections in a map area quickly by sorting them into square tiles."""

    DEFAULT_TILE_SIZE = 256.0

    def __init__(self, tile_size=DEFAULT_TILE_SIZE):
        self.tile_size = self._validate_tile_size(tile_size)

        # Each tile maps connection key -> ConnectionData, so single
        # connections can be replaced without scanning a whole tile.
        self.connections_by_tile = defaultdict(dict)

        self._connections_by_key = {}

        self._connection_keys_by_node_id = defaultdict(set)

        self.connection_count = 0

    def clear(self):
        self.connections_by_tile.clear()
        self._connections_by_key.clear()
        self._connection_keys_by_node_id.clear()

        self.connection_count = 0

    def build(self, autodrive_data: AutoDriveData):
        self.clear()

        for source_node in autodrive_data.get_sorted_nodes():
            for target_id in sorted(source_node.outgoing):
                target_node = autodrive_data.get_node(target_id)

                if target_node is None:
                    continue

                connection_type = get_connection_type(source_node, target_node)

                connection_data = ConnectionData(
                    source_id=source_node.node_id,
                    target_id=target_node.node_id,
                    source_x=source_node.x,
                    source_z=source_node.z,
                    target_x=target_node.x,
                    target_z=target_node.z,
                    connection_type=connection_type,
                )

                if connection_data.key in self._connections_by_key:
                    continue

                self._add_connection(connection_data)

        self.connection_count = len(self._connections_by_key)

    def update_node_positions(self, autodrive_data: AutoDriveData, node_ids):
        """Updates all connections touching the given nodes to the
        nodes' current positions. Connection types stay unchanged."""

        affected_keys = set()

        for node_id in node_ids:
            affected_keys.update(self._connection_keys_by_node_id.get(node_id, ()))

        for connection_key in affected_keys:
            old_connection = self._connections_by_key[connection_key]

            source_node = autodrive_data.get_node(old_connection.source_id)

            target_node = autodrive_data.get_node(old_connection.target_id)

            if source_node is None or target_node is None:
                continue

            self._remove_connection(old_connection)

            self._add_connection(
                ConnectionData(
                    source_id=old_connection.source_id,
                    target_id=old_connection.target_id,
                    source_x=source_node.x,
                    source_z=source_node.z,
                    target_x=target_node.x,
                    target_z=target_node.z,
                    connection_type=old_connection.connection_type,
                )
            )

    def rebuild_node_connections(self, autodrive_data: AutoDriveData, node_ids):
        """Re-creates all connections touching the given nodes from
        the current data. Nodes that no longer exist lose all their
        connections. Pass every node whose incoming or outgoing set
        changed, so one-way connections are found from both ends."""

        node_ids = set(node_ids)

        # The other ends of removed connections are checked again too.
        # A reverse connection into a rebuilt node is only stored in
        # the source node's outgoing set and would otherwise be lost.
        nodes_to_check = set(node_ids)

        for node_id in node_ids:
            for connection_key in list(self._connection_keys_by_node_id.get(node_id, ())):
                connection = self._connections_by_key[connection_key]

                nodes_to_check.update((connection.source_id, connection.target_id))

                self._remove_connection(connection)

        for node_id in nodes_to_check:
            node = autodrive_data.get_node(node_id)

            if node is None:
                continue

            candidate_pairs = [
                (node, autodrive_data.get_node(target_id)) for target_id in node.outgoing
            ] + [(autodrive_data.get_node(source_id), node) for source_id in node.incoming]

            for source_node, target_node in candidate_pairs:
                if (
                    source_node is None
                    or target_node is None
                    or target_node.node_id not in source_node.outgoing
                ):
                    continue

                connection_data = ConnectionData(
                    source_id=source_node.node_id,
                    target_id=target_node.node_id,
                    source_x=source_node.x,
                    source_z=source_node.z,
                    target_x=target_node.x,
                    target_z=target_node.z,
                    connection_type=get_connection_type(source_node, target_node),
                )

                if connection_data.key in self._connections_by_key:
                    continue

                self._add_connection(connection_data)

        self.connection_count = len(self._connections_by_key)

    def get_connections_in_rect(self, visible_rect: QRectF):
        if visible_rect.isEmpty():
            return []

        minimum_tile_x = math.floor(visible_rect.left() / self.tile_size)

        maximum_tile_x = math.floor(visible_rect.right() / self.tile_size)

        minimum_tile_z = math.floor(visible_rect.top() / self.tile_size)

        maximum_tile_z = math.floor(visible_rect.bottom() / self.tile_size)

        visible_connections = []
        seen_connections = set()

        for tile_x in range(minimum_tile_x, maximum_tile_x + 1):
            for tile_z in range(minimum_tile_z, maximum_tile_z + 1):
                tile_connections = self.connections_by_tile.get((tile_x, tile_z), {})

                for connection_key, connection in tile_connections.items():
                    if connection_key in seen_connections:
                        continue

                    seen_connections.add(connection_key)

                    if not connection.intersects_rect(visible_rect):
                        continue

                    visible_connections.append(connection)

        return visible_connections

    def _add_connection(self, connection_data: ConnectionData):
        connection_key = connection_data.key

        for tile_key in self._get_tile_keys(connection_data):
            self.connections_by_tile[tile_key][connection_key] = connection_data

        self._connections_by_key[connection_key] = connection_data

        self._connection_keys_by_node_id[connection_data.source_id].add(connection_key)

        self._connection_keys_by_node_id[connection_data.target_id].add(connection_key)

    def _remove_connection(self, connection_data: ConnectionData):
        connection_key = connection_data.key

        for tile_key in self._get_tile_keys(connection_data):
            tile_connections = self.connections_by_tile.get(tile_key)

            if tile_connections is None:
                continue

            tile_connections.pop(connection_key, None)

            if not tile_connections:
                del self.connections_by_tile[tile_key]

        self._connections_by_key.pop(connection_key, None)

        for node_id in (connection_data.source_id, connection_data.target_id):
            node_keys = self._connection_keys_by_node_id.get(node_id)

            if node_keys is None:
                continue

            node_keys.discard(connection_key)

            if not node_keys:
                del self._connection_keys_by_node_id[node_id]

    def _get_tile_keys(self, connection_data: ConnectionData):
        minimum_tile_x = math.floor(connection_data.minimum_x / self.tile_size)

        maximum_tile_x = math.floor(connection_data.maximum_x / self.tile_size)

        minimum_tile_z = math.floor(connection_data.minimum_z / self.tile_size)

        maximum_tile_z = math.floor(connection_data.maximum_z / self.tile_size)

        for tile_x in range(minimum_tile_x, maximum_tile_x + 1):
            for tile_z in range(minimum_tile_z, maximum_tile_z + 1):
                yield (tile_x, tile_z)

    @staticmethod
    def _validate_tile_size(tile_size):
        tile_size = float(tile_size)

        if tile_size <= 0:
            raise ValueError("Die Connection-Kachelgröße muss größer als 0 sein.")

        return tile_size
