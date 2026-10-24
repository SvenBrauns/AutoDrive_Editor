from PySide6.QtCore import QRectF
from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsScene
)

from autodrive.models import NodeData
from rendering.items.node_item import NodeItem
from rendering.display_style import DisplayStyle
from rendering.node_spatial_index import (
    NodeSpatialIndex
)


class VisibleNodeManager:

    DEFAULT_PADDING = 128.0

    def __init__(
        self,
        scene: QGraphicsScene,
        node_layer: QGraphicsItem,
        node_spatial_index: NodeSpatialIndex,
        display_style: DisplayStyle,
        padding: float = DEFAULT_PADDING
    ):
        self.scene = scene
        self.node_layer = node_layer
        self.node_spatial_index = (
            node_spatial_index
        )

        self.display_style = display_style

        self.padding = max(
            0.0,
            float(padding)
        )

        self.visible_node_items: dict[
            int,
            NodeItem
        ] = {}

    def update(
        self,
        visible_rect: QRectF
    ):
        required_nodes = (
            self.node_spatial_index.get_nodes_in_rect(
                visible_rect,
                padding=self.padding
            )
        )

        required_nodes_by_id = {
            node_data.node_id: node_data
            for node_data in required_nodes
        }

        required_node_ids = set(
            required_nodes_by_id
        )

        existing_node_ids = set(
            self.visible_node_items
        )

        node_ids_to_remove = (
            existing_node_ids
            - required_node_ids
        )

        node_ids_to_add = (
            required_node_ids
            - existing_node_ids
        )

        for node_id in node_ids_to_remove:
            self._remove_node_item(
                node_id
            )

        for node_id in node_ids_to_add:
            self._add_node_item(
                required_nodes_by_id[
                    node_id
                ]
            )

    def clear(self):
        for node_id in list(
            self.visible_node_items
        ):
            self._remove_node_item(
                node_id
            )

    def _add_node_item(
        self,
        node_data: NodeData
    ):
        node_item = NodeItem(
            node_data=node_data,
            display_style=self.display_style
        )

        node_item.setParentItem(
            self.node_layer
        )

        self.visible_node_items[
            node_data.node_id
        ] = node_item

    def _remove_node_item(
        self,
        node_id: int
    ):
        node_item = self.visible_node_items.pop(
            node_id,
            None
        )

        if node_item is None:
            return

        if node_item.scene() is self.scene:
            self.scene.removeItem(
                node_item
            )