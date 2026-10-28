import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QPainterPath, QPolygonF
from PySide6.QtWidgets import QGraphicsScene

from autodrive_editor.file_io.savegame_sheds import IndoorArea
from autodrive_editor.model.autodrive_data import AutoDriveData, MarkerData, NodeData
from autodrive_editor.rendering.connections.connection_data import ConnectionData
from autodrive_editor.rendering.display_style import DisplayStyle
from autodrive_editor.rendering.layers.connection_layer import ConnectionLayerItem
from autodrive_editor.rendering.layers.marker_layer import MarkerLayerItem
from autodrive_editor.rendering.layers.network_tiles import NetworkTiles
from autodrive_editor.rendering.layers.node_label_layer import NodeLabelLayerItem
from autodrive_editor.rendering.layers.node_layer import (
    NodeLayerItem,
    node_diameter_px,
    node_opacity,
)
from autodrive_editor.rendering.layers.selection_layer import (
    SelectionLayerItem,
    selected_node_diameter_px,
    selection_ring_px,
)
from autodrive_editor.rendering.layers.shed_layer import ShedLayerItem
from autodrive_editor.rendering.spatial.connection_index import ConnectionSpatialIndex
from autodrive_editor.rendering.spatial.node_index import NodeSpatialIndex
from autodrive_editor.rendering.visibility import Visibility

# Nodes can be clicked within this distance on screen, even when drawn smaller.
NODE_HIT_MIN_PX = 4.0


class SceneRenderer:
    """Draws the AutoDrive network with five layer items: connections, nodes, node IDs, markers
    and the selection, plus the sheds of the savegame below them. Each layer paints straight from
    the spatial indexes, so there are no graphics items per node, and sizes follow the zoom
    smoothly (see DisplayStyle). After edits, apply_changes updates the indexes; only the changed
    map tiles are drawn anew.
    """

    SPATIAL_TILE_SIZE = 256.0

    def __init__(
        self, scene: QGraphicsScene, marker_icon_path, display_style: DisplayStyle | None = None
    ):
        self.scene = scene
        self.display_style = display_style if display_style is not None else DisplayStyle()
        self.marker_icon_path = str(marker_icon_path)

        self.node_spatial_index = NodeSpatialIndex(tile_size=self.SPATIAL_TILE_SIZE)
        self.connection_spatial_index = ConnectionSpatialIndex(tile_size=self.SPATIAL_TILE_SIZE)
        self.tiles = NetworkTiles(self.node_spatial_index, self.connection_spatial_index)

        self.marker_names_visible = True
        self.visibility = Visibility()
        # Markers vehicles park at (savegames).
        self.parking_markers: list[MarkerData] = []
        # Indoor areas of the buildings in the savegame.
        self.shed_areas: list[IndoorArea] = []
        self.selected_node_ids: set[int] = set()

        self.autodrive_data: AutoDriveData | None = None
        # Area of all nodes. It only grows while editing, which is enough for the layer bounds.
        self.network_bounds = QRectF()

        self.connection_layer: ConnectionLayerItem | None = None
        self.node_layer: NodeLayerItem | None = None
        self.node_label_layer: NodeLabelLayerItem | None = None
        self.marker_layer: MarkerLayerItem | None = None
        self.selection_layer: SelectionLayerItem | None = None
        self.shed_layer: ShedLayerItem | None = None

    @property
    def layers(self) -> list:
        return [
            layer
            for layer in (
                self.shed_layer,
                self.connection_layer,
                self.node_layer,
                self.node_label_layer,
                self.marker_layer,
                self.selection_layer,
            )
            if layer is not None
        ]

    def render(self, autodrive_data: AutoDriveData):
        self.reset()

        self.autodrive_data = autodrive_data

        self.node_spatial_index.build(autodrive_data)
        self.connection_spatial_index.build(autodrive_data)

        style = self.display_style

        self.connection_layer = ConnectionLayerItem(self.tiles, style)
        self.node_layer = NodeLayerItem(self.tiles, style)
        self.node_label_layer = NodeLabelLayerItem(self.node_spatial_index, style)
        self.marker_layer = MarkerLayerItem(autodrive_data, self.marker_icon_path, style)
        self.marker_layer.set_names_visible(self.marker_names_visible)
        self.marker_layer.set_parking_markers(self.parking_markers)
        self.selection_layer = SelectionLayerItem(style)
        self.shed_layer = ShedLayerItem(style)

        self.network_bounds = _get_bounds(autodrive_data.nodes.values())

        for layer in self.layers:
            layer.set_network_bounds(self.network_bounds)
            layer.set_visibility(self.visibility)
            self.scene.addItem(layer)

        self.shed_layer.set_areas(self.shed_areas)

        self._refresh_selection()

    def reset(self):
        for layer in self.layers:
            if layer.scene() is self.scene:
                self.scene.removeItem(layer)

        self.connection_layer = None
        self.node_layer = None
        self.node_label_layer = None
        self.marker_layer = None
        self.selection_layer = None
        self.shed_layer = None

        self.parking_markers = []
        self.shed_areas = []

        self.node_spatial_index.clear()
        self.connection_spatial_index.clear()
        self.tiles.clear()

        self.selected_node_ids.clear()
        self.autodrive_data = None
        self.network_bounds = QRectF()

    def update_node_positions(self, node_ids):
        """Moves the drawn nodes, markers, selection and connections to the nodes' current
        positions."""

        self.apply_changes(moved_node_ids=node_ids)

    def apply_changes(
        self,
        moved_node_ids=(),
        added_node_ids=(),
        removed_node_ids=(),
        connection_node_ids=(),
        changed_flag_node_ids=(),
        changed_marker_node_ids=(),
    ):
        """Updates the drawing after an edit without rebuilding everything.

        moved_node_ids:      nodes whose position changed
        added_node_ids:      nodes added to the data
        removed_node_ids:    nodes removed from the data
        connection_node_ids: nodes whose connections changed
        changed_flag_node_ids: nodes whose flag changed
        changed_marker_node_ids: nodes whose marker changed
        """

        if self.autodrive_data is None:
            return

        nodes = self.autodrive_data.nodes

        moved_nodes = [nodes[node_id] for node_id in moved_node_ids if node_id in nodes]
        added_nodes = [nodes[node_id] for node_id in added_node_ids if node_id in nodes]
        removed_node_ids = set(removed_node_ids)

        self.node_spatial_index.remove_nodes(removed_node_ids)
        self.node_spatial_index.add_nodes(added_nodes)
        self.node_spatial_index.update_nodes(moved_nodes)
        self.node_spatial_index.mark_nodes_changed(changed_flag_node_ids)

        self.connection_spatial_index.update_node_positions(
            self.autodrive_data, [node.node_id for node in moved_nodes]
        )

        rebuilt_node_ids = removed_node_ids | set(added_node_ids) | set(connection_node_ids)

        if rebuilt_node_ids:
            self.connection_spatial_index.rebuild_node_connections(
                self.autodrive_data, rebuilt_node_ids
            )

        if moved_nodes or added_nodes:
            self.network_bounds = self.network_bounds.united(_get_bounds(moved_nodes + added_nodes))

            for layer in self.layers:
                layer.set_network_bounds(self.network_bounds)

        self.selected_node_ids -= removed_node_ids

        self._refresh_selection()

        for layer in self.layers:
            layer.update()

        if self.marker_layer is not None:
            self.marker_layer.invalidate()

    def set_selected_node_ids(self, node_ids):
        self.selected_node_ids = {int(node_id) for node_id in node_ids}

        self._refresh_selection()

    def _refresh_selection(self):
        if self.selection_layer is None or self.autodrive_data is None:
            return

        nodes = self.autodrive_data.nodes

        self.selection_layer.set_nodes(
            nodes[node_id] for node_id in self.selected_node_ids if node_id in nodes
        )

    def get_nodes_in_selection_path(self, selection_path: QPainterPath) -> list[NodeData]:
        """Nodes inside the path. None while nodes are hidden and hidden items are not
        selectable."""

        if not self.visibility.nodes_selectable:
            return []

        return self.node_spatial_index.get_nodes_in_path(selection_path)

    def get_node_at(self, x: float, z: float, zoom_level: float) -> NodeData | None:
        """The drawn node closest to the scene point, if the point is on it or within
        NODE_HIT_MIN_PX on screen. While nodes fade out when zoomed out, only selected nodes
        count. Nodes switched off count only when hidden items are selectable."""

        if zoom_level <= 0 or not self.visibility.nodes_selectable:
            return None

        style = self.display_style
        nodes_drawn = node_opacity(style, zoom_level) > 0

        node_radius = max(node_diameter_px(style, zoom_level) / 2, NODE_HIT_MIN_PX) / zoom_level
        selected_radius = (
            max(
                selected_node_diameter_px(style, zoom_level) / 2
                + selection_ring_px(style, zoom_level),
                NODE_HIT_MIN_PX,
            )
            / zoom_level
        )

        search_radius = max(node_radius, selected_radius)
        search_rect = QRectF(
            x - search_radius, z - search_radius, 2 * search_radius, 2 * search_radius
        )

        closest, closest_distance = None, math.inf

        for node in self.node_spatial_index.get_nodes_in_rect(search_rect):
            if node.node_id in self.selected_node_ids:
                radius = selected_radius

            elif nodes_drawn:
                radius = node_radius

            else:
                continue

            distance = math.hypot(node.x - x, node.z - z)

            if distance <= radius and distance < closest_distance:
                closest, closest_distance = node, distance

        return closest

    def get_shed_at(self, x: float, z: float) -> IndoorArea | None:
        """The shed whose outline contains the scene point, while sheds are shown."""

        if not self.visibility.sheds:
            return None

        point = QPointF(x, z)

        for area in self.shed_areas:
            outline = QPolygonF([QPointF(*corner) for corner in area.corners])

            if outline.containsPoint(point, Qt.OddEvenFill):
                return area

        return None

    def get_connection_at(self, x: float, z: float, tolerance: float) -> ConnectionData | None:
        """The connection closest to the scene point, if it is within
        tolerance (in scene units). Hidden types count only when hidden items are selectable."""

        search_rect = QRectF(x - tolerance, z - tolerance, 2 * tolerance, 2 * tolerance)

        closest, closest_distance = None, tolerance

        for connection in self.connection_spatial_index.get_connections_in_rect(search_rect):
            if not self.visibility.connection_selectable(connection.connection_type):
                continue

            distance = _distance_to_segment(
                x,
                z,
                connection.source_x,
                connection.source_z,
                connection.target_x,
                connection.target_z,
            )

            if distance <= closest_distance:
                closest, closest_distance = connection, distance

        return closest

    def get_debug_state(self) -> dict:
        return {
            "total_nodes": self.node_spatial_index.node_count,
            "total_connections": self.connection_spatial_index.connection_count,
            "selected_nodes": len(self.selected_node_ids),
            "cached_tiles": len(self.tiles.connection_tiles) + len(self.tiles.node_tiles),
            "drawn_arrows": self.connection_layer.drawn_arrows if self.connection_layer else 0,
            "drawn_markers": self.marker_layer.drawn_markers if self.marker_layer else 0,
        }

    def set_marker_names_visible(self, visible: bool):
        self.marker_names_visible = bool(visible)

        if self.marker_layer is not None:
            self.marker_layer.set_names_visible(self.marker_names_visible)

    def set_visibility(self, visibility: Visibility):
        self.visibility = visibility

        for layer in self.layers:
            layer.set_visibility(visibility)

    def set_parking_markers(self, markers):
        self.parking_markers = list(markers)

        if self.marker_layer is not None:
            self.marker_layer.set_parking_markers(self.parking_markers)

    def set_shed_areas(self, areas: list[IndoorArea]):
        self.shed_areas = list(areas)

        if self.shed_layer is not None:
            self.shed_layer.set_areas(self.shed_areas)

    def set_display_style(self, display_style: DisplayStyle):
        if not isinstance(display_style, DisplayStyle):
            raise TypeError("Invalid display style.")

        self.display_style = display_style

        for layer in self.layers:
            layer.set_display_style(display_style)


def _get_bounds(nodes) -> QRectF:
    xs, zs = [], []

    for node in nodes:
        xs.append(node.x)
        zs.append(node.z)

    if not xs:
        return QRectF()

    # At least 1 m wide and high: rectangles without area are ignored when united.
    return QRectF(min(xs), min(zs), max(max(xs) - min(xs), 1.0), max(max(zs) - min(zs), 1.0))


def _distance_to_segment(x, z, x1, z1, x2, z2) -> float:
    dx, dz = x2 - x1, z2 - z1
    length_squared = dx * dx + dz * dz

    if length_squared == 0:
        return math.hypot(x - x1, z - z1)

    t = max(0.0, min(1.0, ((x - x1) * dx + (z - z1) * dz) / length_squared))

    return math.hypot(x - (x1 + t * dx), z - (z1 + t * dz))
