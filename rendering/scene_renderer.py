from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import (
    QColor,
    QPainterPath,
    QPen
)
from PySide6.QtWidgets import (
    QGraphicsPathItem,
    QGraphicsScene
)

from autodrive.models import (
    AutoDriveData,
    NodeData
)

from items.marker_item import MarkerItem
from items.node_item import NodeItem
from rendering.graphics_layer import GraphicsLayerItem


class SceneRenderer:

    BACKGROUND_Z_VALUE = -1000
    CONNECTION_Z_VALUE = -10
    NODE_Z_VALUE = 0
    MARKER_Z_VALUE = 10

    DEFAULT_NODE_MIN_ZOOM = 1.0
    DEFAULT_MARKER_MIN_ZOOM = 1.0

    CONNECTION_REGULAR = "regular"
    CONNECTION_DUAL = "dual"
    CONNECTION_REVERSE = "reverse"

    def __init__(
        self,
        scene: QGraphicsScene,
        marker_icon_path
    ):
        self.scene = scene

        self.marker_icon_path = str(
            marker_icon_path
        )

        self.node_items = {}

        self.node_layer = None
        self.marker_layer = None

        self.connection_items = {}

        self.node_min_zoom = (
            self.DEFAULT_NODE_MIN_ZOOM
        )

        self.marker_min_zoom = (
            self.DEFAULT_MARKER_MIN_ZOOM
        )

        self.current_zoom = None

        self.nodes_visible = None
        self.markers_visible = None

        self.regular_pen = QPen(
            QColor(0, 255, 0)
        )

        self.dual_pen = QPen(
            QColor(0, 0, 255)
        )

        self.reverse_pen = QPen(
            QColor(100, 220, 255)
        )

    def render(
        self,
        autodrive_data: AutoDriveData,
        on_node_selected: (
            Callable[[NodeData], None] | None
        ) = None
    ):
        self.reset()

        self._create_layers()

        self._render_nodes(
            autodrive_data,
            on_node_selected
        )

        self.rebuild_connections(
            autodrive_data
        )

        self._render_markers(
            autodrive_data
        )

        if self.current_zoom is not None:
            self.update_visibility_for_zoom(
                self.current_zoom
            )

    def reset(self):
        self.node_items.clear()
        self.connection_items.clear()

        self.node_layer = None
        self.marker_layer = None

        self.nodes_visible = None
        self.markers_visible = None

    def get_node_item(
        self,
        node_id: int
    ):
        return self.node_items.get(
            node_id
        )

    def update_visibility_for_zoom(
        self,
        zoom_level
    ):
        zoom_level = float(
            zoom_level
        )

        self.current_zoom = zoom_level

        show_nodes = (
            zoom_level >= self.node_min_zoom
        )

        show_markers = (
            zoom_level >= self.marker_min_zoom
        )

        if (
            self.node_layer is not None
            and show_nodes != self.nodes_visible
        ):
            self.node_layer.setVisible(
                show_nodes
            )

            self.nodes_visible = show_nodes

        if (
            self.marker_layer is not None
            and show_markers != self.markers_visible
        ):
            self.marker_layer.setVisible(
                show_markers
            )

            self.markers_visible = show_markers

    def set_visibility_thresholds(
        self,
        node_min_zoom=None,
        marker_min_zoom=None
    ):
        if node_min_zoom is not None:
            node_min_zoom = float(
                node_min_zoom
            )

            if node_min_zoom < 0:
                raise ValueError(
                    "Der Mindestzoom für Nodes darf "
                    "nicht negativ sein."
                )

            self.node_min_zoom = node_min_zoom

        if marker_min_zoom is not None:
            marker_min_zoom = float(
                marker_min_zoom
            )

            if marker_min_zoom < 0:
                raise ValueError(
                    "Der Mindestzoom für Marker darf "
                    "nicht negativ sein."
                )

            self.marker_min_zoom = marker_min_zoom

        if self.current_zoom is not None:
            self.nodes_visible = None
            self.markers_visible = None

            self.update_visibility_for_zoom(
                self.current_zoom
            )

    def rebuild_connections(
        self,
        autodrive_data: AutoDriveData
    ):
        self._remove_connection_items()

        connection_paths = {
            self.CONNECTION_REGULAR: QPainterPath(),
            self.CONNECTION_DUAL: QPainterPath(),
            self.CONNECTION_REVERSE: QPainterPath()
        }

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
                    self._get_connection_type(
                        source_node,
                        target_node
                    )
                )

                connection_path = (
                    connection_paths[
                        connection_type
                    ]
                )

                connection_path.moveTo(
                    source_node.x,
                    source_node.z
                )

                connection_path.lineTo(
                    target_node.x,
                    target_node.z
                )

        connection_pens = {
            self.CONNECTION_REGULAR: (
                self.regular_pen
            ),
            self.CONNECTION_DUAL: (
                self.dual_pen
            ),
            self.CONNECTION_REVERSE: (
                self.reverse_pen
            )
        }

        for (
            connection_type,
            connection_path
        ) in connection_paths.items():
            connection_item = (
                self._create_connection_item(
                    connection_path,
                    connection_pens[
                        connection_type
                    ]
                )
            )

            if connection_item is not None:
                self.connection_items[
                    connection_type
                ] = connection_item

    def _create_layers(self):
        self.node_layer = GraphicsLayerItem()

        self.node_layer.setZValue(
            self.NODE_Z_VALUE
        )

        self.scene.addItem(
            self.node_layer
        )

        self.marker_layer = GraphicsLayerItem()

        self.marker_layer.setZValue(
            self.MARKER_Z_VALUE
        )

        self.scene.addItem(
            self.marker_layer
        )

    def _render_nodes(
        self,
        autodrive_data: AutoDriveData,
        on_node_selected: (
            Callable[[NodeData], None] | None
        )
    ):
        for node_data in (
            autodrive_data.get_sorted_nodes()
        ):
            node_item = NodeItem(
                node_data=node_data,
                on_selected=on_node_selected
            )

            node_item.setParentItem(
                self.node_layer
            )

            self.node_items[
                node_data.node_id
            ] = node_item

    def _render_markers(
        self,
        autodrive_data: AutoDriveData
    ):
        for marker_data in (
            autodrive_data.markers.values()
        ):
            node_item = self.get_node_item(
                marker_data.node_id
            )

            if node_item is None:
                continue

            marker_item = MarkerItem(
                self.marker_icon_path
            )

            marker_item.setScale(
                0.15
            )

            marker_item.setPos(
                node_item.pos().x() - 5,
                node_item.pos().y() - 12
            )

            marker_item.setParentItem(
                self.marker_layer
            )

    def _create_connection_item(
        self,
        connection_path,
        connection_pen
    ):
        if connection_path.isEmpty():
            return None

        connection_item = QGraphicsPathItem(
            connection_path
        )

        connection_item.setPen(
            connection_pen
        )

        connection_item.setZValue(
            self.CONNECTION_Z_VALUE
        )

        connection_item.setAcceptedMouseButtons(
            Qt.NoButton
        )

        self.scene.addItem(
            connection_item
        )

        return connection_item

    def _remove_connection_items(self):
        for connection_item in (
            self.connection_items.values()
        ):
            if (
                connection_item.scene()
                is self.scene
            ):
                self.scene.removeItem(
                    connection_item
                )

        self.connection_items.clear()

    def _get_connection_type(
        self,
        source_node: NodeData,
        target_node: NodeData
    ):
        if self._is_dual_connection(
            source_node,
            target_node
        ):
            return self.CONNECTION_DUAL

        if self._is_reverse_connection(
            source_node,
            target_node
        ):
            return self.CONNECTION_REVERSE

        return self.CONNECTION_REGULAR

    @staticmethod
    def _is_dual_connection(
        source_node: NodeData,
        target_node: NodeData
    ):
        return (
            target_node.node_id
            in source_node.outgoing
            and target_node.node_id
            in source_node.incoming
            and source_node.node_id
            in target_node.outgoing
            and source_node.node_id
            in target_node.incoming
        )

    @staticmethod
    def _is_reverse_connection(
        source_node: NodeData,
        target_node: NodeData
    ):
        return (
            target_node.node_id
            in source_node.outgoing
            and source_node.node_id
            not in target_node.incoming
        )