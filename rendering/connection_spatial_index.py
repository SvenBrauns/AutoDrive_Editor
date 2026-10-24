import math

from collections import defaultdict

from PySide6.QtCore import QRectF

from autodrive.models import AutoDriveData
from rendering.connection_render_data import (
    ConnectionRenderData
)


class ConnectionSpatialIndex:

    DEFAULT_TILE_SIZE = 256.0

    def __init__(
        self,
        tile_size=DEFAULT_TILE_SIZE
    ):
        self.tile_size = self._validate_tile_size(
            tile_size
        )

        self.connections_by_tile = defaultdict(
            list
        )

        self.connection_count = 0

    def clear(self):
        self.connections_by_tile.clear()

        self.connection_count = 0

    def build(
        self,
        autodrive_data: AutoDriveData,
        connection_type_resolver
    ):
        self.clear()

        seen_connections = set()

        for source_node in (
            autodrive_data.get_sorted_nodes()
        ):
            for target_id in sorted(
                source_node.outgoing
            ):
                target_node = (
                    autodrive_data.get_node(
                        target_id
                    )
                )

                if target_node is None:
                    continue

                connection_type = (
                    connection_type_resolver(
                        source_node,
                        target_node
                    )
                )

                if connection_type == "dual":
                    connection_key = (
                        connection_type,
                        min(
                            source_node.node_id,
                            target_node.node_id
                        ),
                        max(
                            source_node.node_id,
                            target_node.node_id
                        )
                    )

                else:
                    connection_key = (
                        connection_type,
                        source_node.node_id,
                        target_node.node_id
                    )

                if connection_key in seen_connections:
                    continue

                seen_connections.add(
                    connection_key
                )

                connection_data = (
                    ConnectionRenderData(
                        source_id=source_node.node_id,
                        target_id=target_node.node_id,
                        source_x=source_node.x,
                        source_z=source_node.z,
                        target_x=target_node.x,
                        target_z=target_node.z,
                        connection_type=connection_type
                    )
                )

                self._add_connection(
                    connection_data
                )

                self.connection_count += 1

    def get_connections_in_rect(
        self,
        visible_rect: QRectF
    ):
        if visible_rect.isEmpty():
            return []

        minimum_tile_x = math.floor(
            visible_rect.left()
            / self.tile_size
        )

        maximum_tile_x = math.floor(
            visible_rect.right()
            / self.tile_size
        )

        minimum_tile_z = math.floor(
            visible_rect.top()
            / self.tile_size
        )

        maximum_tile_z = math.floor(
            visible_rect.bottom()
            / self.tile_size
        )

        visible_connections = []
        seen_connections = set()

        for tile_x in range(
            minimum_tile_x,
            maximum_tile_x + 1
        ):
            for tile_z in range(
                minimum_tile_z,
                maximum_tile_z + 1
            ):
                tile_connections = (
                    self.connections_by_tile.get(
                        (
                            tile_x,
                            tile_z
                        ),
                        ()
                    )
                )

                for connection in tile_connections:
                    connection_key = connection.key

                    if connection_key in seen_connections:
                        continue

                    seen_connections.add(
                        connection_key
                    )

                    if not connection.intersects_rect(
                        visible_rect
                    ):
                        continue

                    visible_connections.append(
                        connection
                    )

        return visible_connections

    def _add_connection(
        self,
        connection_data
    ):
        minimum_x = min(
            connection_data.source_x,
            connection_data.target_x
        )

        maximum_x = max(
            connection_data.source_x,
            connection_data.target_x
        )

        minimum_z = min(
            connection_data.source_z,
            connection_data.target_z
        )

        maximum_z = max(
            connection_data.source_z,
            connection_data.target_z
        )

        minimum_tile_x = math.floor(
            minimum_x / self.tile_size
        )

        maximum_tile_x = math.floor(
            maximum_x / self.tile_size
        )

        minimum_tile_z = math.floor(
            minimum_z / self.tile_size
        )

        maximum_tile_z = math.floor(
            maximum_z / self.tile_size
        )

        for tile_x in range(
            minimum_tile_x,
            maximum_tile_x + 1
        ):
            for tile_z in range(
                minimum_tile_z,
                maximum_tile_z + 1
            ):
                self.connections_by_tile[
                    (
                        tile_x,
                        tile_z
                    )
                ].append(
                    connection_data
                )

    @staticmethod
    def _validate_tile_size(
        tile_size
    ):
        tile_size = float(
            tile_size
        )

        if tile_size <= 0:
            raise ValueError(
                "Die Connection-Kachelgröße muss "
                "größer als 0 sein."
            )

        return tile_size