from PySide6.QtCore import QRectF
from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsScene
)

from autodrive.models import NodeData
from rendering.display_style import DisplayStyle
from rendering.items.node_selection_item import (
    NodeSelectionItem
)
from rendering.node_spatial_index import (
    NodeSpatialIndex
)


class VisibleNodeSelectionManager:

    DEFAULT_PADDING = 128.0

    def __init__(
        self,
        scene: QGraphicsScene,
        selection_layer: QGraphicsItem,
        node_spatial_index: NodeSpatialIndex,
        display_style: DisplayStyle,
        padding: float = DEFAULT_PADDING
    ):
        self.scene = scene
        self.selection_layer = selection_layer
        self.node_spatial_index = (
            node_spatial_index
        )
        self.display_style = display_style

        self.padding = max(
            0.0,
            float(padding)
        )

        self.selected_node_ids: set[int] = set()

        self.visible_selection_items: dict[
            int,
            NodeSelectionItem
        ] = {}

        self.current_visible_rect: QRectF | None = None

    def set_selected_node_ids(
        self,
        node_ids
    ):
        self.selected_node_ids = {
            int(node_id)
            for node_id in node_ids
        }

        if self.current_visible_rect is not None:
            self.update(
                self.current_visible_rect
            )

    def update(
        self,
        visible_rect: QRectF
    ):
        self.current_visible_rect = QRectF(
            visible_rect
        )

        visible_nodes = (
            self.node_spatial_index.get_nodes_in_rect(
                visible_rect,
                padding=self.padding
            )
        )

        selected_visible_nodes = {
            node_data.node_id: node_data
            for node_data in visible_nodes
            if node_data.node_id
            in self.selected_node_ids
        }

        required_node_ids = set(
            selected_visible_nodes
        )

        existing_node_ids = set(
            self.visible_selection_items
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
            self._remove_selection_item(
                node_id
            )

        for node_id in node_ids_to_add:
            self._add_selection_item(
                selected_visible_nodes[
                    node_id
                ]
            )

    def clear(self):
        for node_id in list(
            self.visible_selection_items
        ):
            self._remove_selection_item(
                node_id
            )

        self.current_visible_rect = None

    def _add_selection_item(
        self,
        node_data: NodeData
    ):
        selection_item = NodeSelectionItem(
            node_data=node_data,
            display_style=self.display_style
        )

        selection_item.setParentItem(
            self.selection_layer
        )

        self.visible_selection_items[
            node_data.node_id
        ] = selection_item

    def _remove_selection_item(
        self,
        node_id: int
    ):
        selection_item = (
            self.visible_selection_items.pop(
                node_id,
                None
            )
        )

        if selection_item is None:
            return

        if selection_item.scene() is self.scene:
            self.scene.removeItem(
                selection_item
            )