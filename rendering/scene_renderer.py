from PySide6.QtCore import (
    QRectF,
    Qt
)
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

from rendering.connection_data import (
    ConnectionType
)
from rendering.connection_geometry import (
    calculate_connection_endpoints,
    get_connection_type
)
from rendering.connection_render_item import (
    ConnectionRenderItem
)
from rendering.connection_spatial_index import (
    ConnectionSpatialIndex
)
from rendering.display_style import DisplayStyle
from rendering.items.graphics_layer import (
    GraphicsLayerItem
)
from rendering.node_spatial_index import (
    NodeSpatialIndex
)
from rendering.visible_marker_manager import (
    VisibleMarkerManager
)
from rendering.visible_node_manager import (
    VisibleNodeManager
)
from rendering.visible_node_selection_manager import (
    VisibleNodeSelectionManager
)


class SceneRenderer:
    
    SPATIAL_TILE_SIZE = 256.0
    VISIBILITY_PADDING = 128.0

    def __init__(
        self,
        scene: QGraphicsScene,
        marker_icon_path,
        display_style: DisplayStyle | None = None
    ):
        self.scene = scene
        self.display_style = (
            display_style
            if display_style is not None
            else DisplayStyle()
        )
        self.marker_icon_path = str(
            marker_icon_path
        )

        self.node_spatial_index = (
            NodeSpatialIndex(
                tile_size=self.SPATIAL_TILE_SIZE
            )
        )

        self.visible_node_manager = None
        self.visible_marker_manager = None
        self.visible_node_selection_manager = None

        self.current_visible_rect = None

        self.node_layer = None
        self.marker_layer = None
        self.selection_layer = None

        self.selected_node_ids: set[int] = set()
        self.connection_items = {}

        self.connection_spatial_index = (
            ConnectionSpatialIndex(
                tile_size=self.SPATIAL_TILE_SIZE
            )
        )

        self.connection_render_item = None

        self.connection_detail_min_zoom = (
            self.display_style.connection_detail_min_zoom
        )

        self.detailed_connections_visible = None

        self.node_min_zoom = (
            self.display_style.node_min_zoom
        )

        self.marker_min_zoom = (
            self.display_style.marker_min_zoom
        )

        self.current_zoom = None

        self.nodes_visible = None
        self.markers_visible = None

        self.connection_pens = (
            self._create_connection_pens()
        )

    def render(
        self,
        autodrive_data: AutoDriveData
    ):
        self.reset()
        self._create_layers()

        self.node_spatial_index.build(
            autodrive_data
        )

        self.visible_node_manager = (
            VisibleNodeManager(
                scene=self.scene,
                node_layer=self.node_layer,
                node_spatial_index=(
                    self.node_spatial_index
                ),
                display_style=self.display_style,
                padding=self.VISIBILITY_PADDING
            )
        )

        self.visible_marker_manager = (
            VisibleMarkerManager(
                scene=self.scene,
                marker_layer=self.marker_layer,
                marker_icon_path=self.marker_icon_path,
                autodrive_data=autodrive_data,
                node_spatial_index=(
                    self.node_spatial_index
                ),
                display_style=self.display_style,
                padding=self.VISIBILITY_PADDING
            )
        )

        self.visible_node_selection_manager = (
            VisibleNodeSelectionManager(
                scene=self.scene,
                selection_layer=self.selection_layer,
                node_spatial_index=(
                    self.node_spatial_index
                ),
                display_style=self.display_style,
                padding=self.VISIBILITY_PADDING
            )
        )

        self.visible_node_selection_manager.set_selected_node_ids(
            self.selected_node_ids
        )

        self.rebuild_connections(
            autodrive_data
        )

        self._create_detailed_connection_renderer(
            autodrive_data
        )

        if self.current_zoom is not None:
            self.update_visibility_for_zoom(
                self.current_zoom
            )

    def reset(self):
        if self.visible_node_manager is not None:
            self.visible_node_manager.clear()

        if self.visible_marker_manager is not None:
            self.visible_marker_manager.clear()

        if self.visible_node_selection_manager is not None:
            self.visible_node_selection_manager.clear()

        self.visible_node_manager = None
        self.visible_marker_manager = None
        self.visible_node_selection_manager = None

        self.node_spatial_index.clear()
        self.current_visible_rect = None

        self.connection_items.clear()

        self.connection_spatial_index.clear()
        self.connection_render_item = None

        self.node_layer = None
        self.marker_layer = None
        self.selection_layer = None
        self.selected_node_ids.clear()

        self.nodes_visible = None
        self.markers_visible = None
        self.detailed_connections_visible = None

    def update_visible_scene_rect(
        self,
        visible_rect: QRectF
    ):
        self.current_visible_rect = QRectF(
            visible_rect
        )

        if (
            self.visible_node_manager is not None
            and self.nodes_visible is True
        ):
            self.visible_node_manager.update(
                self.current_visible_rect
            )

        if (
            self.visible_marker_manager is not None
            and self.markers_visible is True
        ):
            self.visible_marker_manager.update(
                self.current_visible_rect
            )

        if (
            self.visible_node_selection_manager is not None
            and self.nodes_visible is True
        ):
            self.visible_node_selection_manager.update(
                self.current_visible_rect
            )

    def _update_virtualized_layer(
        self,
        layer,
        manager,
        should_be_visible: bool
    ):
        if layer is None:
            return

        layer.setVisible(
            should_be_visible
        )

        if manager is None:
            return

        if should_be_visible:
            if self.current_visible_rect is not None:
                manager.update(
                    self.current_visible_rect
                )

        else:
            manager.clear()

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

        show_detailed_connections = (
            zoom_level
            >= self.connection_detail_min_zoom
        )

        if show_nodes != self.nodes_visible:
            self._update_virtualized_layer(
                layer=self.node_layer,
                manager=self.visible_node_manager,
                should_be_visible=show_nodes
            )

            self._update_virtualized_layer(
                layer=self.selection_layer,
                manager=(
                    self.visible_node_selection_manager
                ),
                should_be_visible=show_nodes
            )

            self.nodes_visible = show_nodes

        if show_markers != self.markers_visible:
            self._update_virtualized_layer(
                layer=self.marker_layer,
                manager=self.visible_marker_manager,
                should_be_visible=show_markers
            )

            self.markers_visible = show_markers

        if (
            show_detailed_connections
            != self.detailed_connections_visible
        ):
            for connection_item in (
                self.connection_items.values()
            ):
                connection_item.setVisible(
                    not show_detailed_connections
                )

            if self.connection_render_item is not None:
                self.connection_render_item.setVisible(
                    show_detailed_connections
                )

            self.detailed_connections_visible = (
                show_detailed_connections
            )

    def set_visibility_thresholds(
        self,
        node_min_zoom=None,
        marker_min_zoom=None,
        connection_detail_min_zoom=None
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

        if connection_detail_min_zoom is not None:
            connection_detail_min_zoom = float(
                connection_detail_min_zoom
            )

            if connection_detail_min_zoom < 0:
                raise ValueError(
                    "Der Mindestzoom für detaillierte "
                    "Connections darf nicht negativ sein."
                )

            self.connection_detail_min_zoom = (
                connection_detail_min_zoom
            )

        if self.current_zoom is not None:
            self.nodes_visible = None
            self.markers_visible = None
            self.detailed_connections_visible = None

            self.update_visibility_for_zoom(
                self.current_zoom
            )

    def rebuild_connections(
        self,
        autodrive_data: AutoDriveData
    ):
        self._remove_connection_items()

        connection_paths = {
            ConnectionType.REGULAR: QPainterPath(),
            ConnectionType.DUAL: QPainterPath(),
            ConnectionType.REVERSE: QPainterPath()
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
                    get_connection_type(
                        source_node,
                        target_node
                    )
                )

                connection_path = (
                    connection_paths[
                        connection_type
                    ]
                )

                endpoints = calculate_connection_endpoints(
                    source_x=source_node.x,
                    source_z=source_node.z,
                    target_x=target_node.x,
                    target_z=target_node.z,
                    node_diameter=(
                        self.display_style.node_diameter
                    )
                )

                if endpoints is None:
                    continue

                start_point, end_point = endpoints

                connection_path.moveTo(
                    start_point
                )

                connection_path.lineTo(
                    end_point
                )

        for (
            connection_type,
            connection_path
        ) in connection_paths.items():
            connection_item = (
                self._create_connection_item(
                    connection_path,
                    self.connection_pens[
                        connection_type
                    ]
                )
            )

            if connection_item is not None:
                self.connection_items[
                    connection_type
                ] = connection_item

    def _create_detailed_connection_renderer(
        self,
        autodrive_data: AutoDriveData
    ):
        self.connection_spatial_index.build(
            autodrive_data
        )

        connection_scene_rect = (
            self.scene.sceneRect()
        )

        if connection_scene_rect.isEmpty():
            connection_scene_rect = (
                self.scene.itemsBoundingRect()
            )

        self.connection_render_item = (
            ConnectionRenderItem(
                spatial_index=(
                    self.connection_spatial_index
                ),
                scene_rect=connection_scene_rect,
                display_style=self.display_style
            )
        )

        self.connection_render_item.setZValue(
            self.display_style.normal_connection_z
            + 0.1
        )

        self.connection_render_item.setVisible(
            False
        )

        self.scene.addItem(
            self.connection_render_item
        )

    def _create_layers(self):
        self.node_layer = GraphicsLayerItem()

        self.node_layer.setZValue(
            self.display_style.normal_node_z
        )

        self.scene.addItem(
            self.node_layer
        )

        self.marker_layer = GraphicsLayerItem()

        self.marker_layer.setZValue(
            self.display_style.normal_marker_z
        )

        self.scene.addItem(
            self.marker_layer
        )

        self.selection_layer = GraphicsLayerItem()

        self.selection_layer.setZValue(
            self.display_style.selected_node_z
        )

        self.scene.addItem(
            self.selection_layer
        )

    def set_selected_node_ids(
        self,
        node_ids
    ):
        self.selected_node_ids = {
            int(node_id)
            for node_id in node_ids
        }

        if (
            self.visible_node_selection_manager
            is not None
        ):
            self.visible_node_selection_manager.set_selected_node_ids(
                self.selected_node_ids
            )

    def get_nodes_in_selection_path(
        self,
        selection_path: QPainterPath
    ) -> list[NodeData]:
        return self.node_spatial_index.get_nodes_in_path(
            selection_path
        )

    def get_debug_state(self) -> dict:
        visible_nodes = 0

        if self.visible_node_manager is not None:
            visible_nodes = len(
                self.visible_node_manager.visible_node_items
            )

        visible_markers = 0

        if self.visible_marker_manager is not None:
            visible_markers = len(
                self.visible_marker_manager.visible_marker_items
            )

        visible_selection_items = 0

        if (
            self.visible_node_selection_manager
            is not None
        ):
            visible_selection_items = len(
                self.visible_node_selection_manager
                .visible_selection_items
            )

        if self.detailed_connections_visible is True:
            connection_mode = "Detail mit Pfeilen"

        elif self.detailed_connections_visible is False:
            connection_mode = "Globale Übersicht"

        else:
            connection_mode = "-"

        return {
            "total_nodes": (
                self.node_spatial_index.node_count
            ),
            "visible_nodes": visible_nodes,
            "visible_markers": visible_markers,
            "selected_nodes": len(
                self.selected_node_ids
            ),
            "visible_selection_items": (
                visible_selection_items
            ),
            "connection_mode": connection_mode,
            "total_connections": (
                self.connection_spatial_index
                .connection_count
            ),
            "nodes_visible": self.nodes_visible,
            "markers_visible": self.markers_visible
        }

    def set_display_style(
        self,
        display_style: DisplayStyle
    ):
        if not isinstance(
            display_style,
            DisplayStyle
        ):
            raise TypeError(
                "Der Darstellungsstil ist ungültig."
            )

        self.display_style = display_style

        self.node_min_zoom = (
            display_style.node_min_zoom
        )

        self.marker_min_zoom = (
            display_style.marker_min_zoom
        )

        self.connection_detail_min_zoom = (
            display_style.connection_detail_min_zoom
        )

        self.connection_pens = (
            self._create_connection_pens()
        )

    def _create_connection_pens(
        self
    ) -> dict[ConnectionType, QPen]:
        return {
            ConnectionType.REGULAR: (
                self._create_connection_pen(
                    self.display_style.regular_connection_color
                )
            ),
            ConnectionType.DUAL: (
                self._create_connection_pen(
                    self.display_style.dual_connection_color
                )
            ),
            ConnectionType.REVERSE: (
                self._create_connection_pen(
                    self.display_style.reverse_connection_color
                )
            )
        }

    def _create_connection_pen(
        self,
        color: tuple[int, int, int]
    ) -> QPen:
        connection_pen = QPen(
            QColor(
                color[0],
                color[1],
                color[2]
            )
        )

        connection_pen.setWidthF(
            self.display_style.connection_width
        )

        connection_pen.setCapStyle(
            Qt.FlatCap
        )

        connection_pen.setJoinStyle(
            Qt.BevelJoin
        )

        return connection_pen

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
            self.display_style.normal_connection_z
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