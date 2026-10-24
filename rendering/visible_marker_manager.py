from PySide6.QtCore import QRectF
from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsScene
)

from autodrive.models import (
    AutoDriveData,
    NodeData
)
from rendering.items.marker_item import MarkerItem
from rendering.display_style import DisplayStyle
from rendering.node_spatial_index import NodeSpatialIndex


class VisibleMarkerManager:

    DEFAULT_PADDING = 128.0

    def __init__(
        self,
        scene: QGraphicsScene,
        marker_layer: QGraphicsItem,
        marker_icon_path,
        autodrive_data: AutoDriveData,
        node_spatial_index: NodeSpatialIndex,
        display_style: DisplayStyle,
        padding=DEFAULT_PADDING
    ):
        self.scene = scene
        self.marker_layer = marker_layer

        self.marker_icon_path = str(
            marker_icon_path
        )

        self.autodrive_data = autodrive_data
        self.node_spatial_index = (
            node_spatial_index
        )
        self.display_style = display_style

        self.padding = max(
            0.0,
            float(padding)
        )

        self.marker_items = {}

    def update(
        self,
        visible_rect: QRectF
    ):
        visible_nodes = (
            self.node_spatial_index.get_nodes_in_rect(
                visible_rect,
                padding=self.padding
            )
        )

        required_nodes_by_id = {
            node_data.node_id: node_data
            for node_data in visible_nodes
            if node_data.node_id
            in self.autodrive_data.markers
        }

        required_marker_ids = set(
            required_nodes_by_id
        )

        existing_marker_ids = set(
            self.marker_items
        )

        marker_ids_to_remove = (
            existing_marker_ids
            - required_marker_ids
        )

        marker_ids_to_add = (
            required_marker_ids
            - existing_marker_ids
        )

        for node_id in marker_ids_to_remove:
            self._remove_marker_item(
                node_id
            )

        for node_id in marker_ids_to_add:
            self._add_marker_item(
                required_nodes_by_id[
                    node_id
                ]
            )

    def clear(self):
        for node_id in list(
            self.marker_items
        ):
            self._remove_marker_item(
                node_id
            )

    def get_marker_item(
        self,
        node_id: int
    ):
        return self.marker_items.get(
            node_id
        )

    def _add_marker_item(
        self,
        node_data: NodeData
    ):
        marker_item = MarkerItem(
            self.marker_icon_path
        )

        marker_scale = (
            self.display_style.marker_scale
        )

        marker_item.setScale(
            marker_scale
        )

        marker_bounds = (
            marker_item.boundingRect()
        )

        anchor_x = (
            marker_bounds.left()
            + marker_bounds.width()
            * self.display_style.marker_anchor_x
        )

        anchor_y = (
            marker_bounds.top()
            + marker_bounds.height()
            * self.display_style.marker_anchor_y
        )

        marker_x = (
            node_data.x
            - anchor_x * marker_scale
        )

        marker_z = (
            node_data.z
            - anchor_y * marker_scale
            - self.display_style.marker_node_gap
        )

        marker_item.setPos(
            marker_x,
            marker_z
        )

        marker_item.setParentItem(
            self.marker_layer
        )

        self.marker_items[
            node_data.node_id
        ] = marker_item

    def _remove_marker_item(
        self,
        node_id: int
    ):
        marker_item = self.marker_items.pop(
            node_id,
            None
        )

        if marker_item is None:
            return

        if marker_item.scene() is self.scene:
            self.scene.removeItem(
                marker_item
            )