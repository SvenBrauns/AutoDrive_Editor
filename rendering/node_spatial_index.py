import math

from collections import defaultdict

from PySide6.QtCore import (
    QPointF,
    QRectF
)
from PySide6.QtGui import QPainterPath

from autodrive.models import (
    AutoDriveData,
    NodeData
)


class NodeSpatialIndex:

    DEFAULT_TILE_SIZE = 256.0

    def __init__(
        self,
        tile_size=DEFAULT_TILE_SIZE
    ):
        self.tile_size = self._validate_tile_size(
            tile_size
        )

        self.nodes_by_tile = defaultdict(
            list
        )

        self.node_count = 0

    def clear(self):
        self.nodes_by_tile.clear()
        self.node_count = 0

    def build(
        self,
        autodrive_data: AutoDriveData
    ):
        self.clear()

        for node_data in (
            autodrive_data.get_sorted_nodes()
        ):
            tile_key = self._get_tile_key(
                node_data.x,
                node_data.z
            )

            self.nodes_by_tile[
                tile_key
            ].append(
                node_data
            )

            self.node_count += 1

    def get_nodes_in_rect(
        self,
        visible_rect: QRectF,
        padding=0.0
    ) -> list[NodeData]:
        padding = max(
            0.0,
            float(padding)
        )

        query_rect = visible_rect.adjusted(
            -padding,
            -padding,
            padding,
            padding
        )

        if query_rect.isEmpty():
            return []

        minimum_tile_x = math.floor(
            query_rect.left()
            / self.tile_size
        )

        maximum_tile_x = math.floor(
            query_rect.right()
            / self.tile_size
        )

        minimum_tile_z = math.floor(
            query_rect.top()
            / self.tile_size
        )

        maximum_tile_z = math.floor(
            query_rect.bottom()
            / self.tile_size
        )

        visible_nodes = []

        for tile_x in range(
            minimum_tile_x,
            maximum_tile_x + 1
        ):
            for tile_z in range(
                minimum_tile_z,
                maximum_tile_z + 1
            ):
                tile_nodes = (
                    self.nodes_by_tile.get(
                        (
                            tile_x,
                            tile_z
                        ),
                        ()
                    )
                )

                for node_data in tile_nodes:
                    if not query_rect.contains(
                        node_data.x,
                        node_data.z
                    ):
                        continue

                    visible_nodes.append(
                        node_data
                    )

        return visible_nodes

    def get_nodes_in_path(
        self,
        selection_path: QPainterPath
    ) -> list[NodeData]:
        if selection_path.isEmpty():
            return []

        path_bounds = (
            selection_path.boundingRect()
        )

        candidate_nodes = self.get_nodes_in_rect(
            path_bounds
        )

        return [
            node_data
            for node_data in candidate_nodes
            if selection_path.contains(
                QPointF(
                    node_data.x,
                    node_data.z
                )
            )
        ]

    def _get_tile_key(
        self,
        x,
        z
    ):
        return (
            math.floor(
                x / self.tile_size
            ),
            math.floor(
                z / self.tile_size
            )
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
                "Die Node-Kachelgröße muss "
                "größer als 0 sein."
            )

        return tile_size