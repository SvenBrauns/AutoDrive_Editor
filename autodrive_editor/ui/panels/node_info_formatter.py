from autodrive_editor.i18n import tr
from autodrive_editor.model.autodrive_data import AutoDriveData, NodeData
from autodrive_editor.terrain.background_map import BackgroundMap
from autodrive_editor.terrain.heightmap import Heightmap


class NodeInfoFormatter:
    """Builds the node info text, including the heightmap height when available."""

    def __init__(self, background_map: BackgroundMap, heightmap: Heightmap):
        self.background_map = background_map
        self.heightmap = heightmap

    def format_node_info(self, node_data: NodeData, autodrive_data: AutoDriveData | None) -> str:
        node_type = self._get_node_type(node_data)

        marker_lines = self._get_marker_lines(node_data, autodrive_data)

        heightmap_lines = self._get_heightmap_lines(node_data)

        info_lines = [
            f"Node {node_data.node_id}",
            "",
            tr("Type: {type}", type=node_type),
            "",
            tr("Coordinates"),
            f"X: {node_data.x:.3f}",
            *heightmap_lines,
            f"Z: {node_data.z:.3f}",
        ]

        if marker_lines:
            info_lines.extend(["", tr("Marker"), *marker_lines])

        return "\n".join(info_lines)

    @staticmethod
    def _get_node_type(node_data: NodeData) -> str:
        if node_data.is_subprio:
            return tr("Subprio node")

        if node_data.is_from_map_scan:
            return tr("Regular node (from map scan)")

        if not node_data.has_known_flag:
            return tr("Regular node (flag {flag})", flag=node_data.flag)

        return tr("Regular node")

    @staticmethod
    def _get_marker_lines(node_data: NodeData, autodrive_data: AutoDriveData | None) -> list[str]:
        if autodrive_data is None:
            return []

        marker_data = autodrive_data.get_marker(node_data.node_id)

        if marker_data is None:
            return []

        return [
            tr("Name: {name}", name=marker_data.name),
            tr("Group: {group}", group=marker_data.group),
        ]

    def _get_heightmap_lines(self, node_data: NodeData) -> list[str]:
        if not self.heightmap.has_heightmap():
            return [f"Y: {node_data.y:.3f}"]

        try:
            height_sample = self.heightmap.get_height_at(
                world_x=node_data.x,
                world_z=node_data.z,
                map_scale=self.background_map.map_scale,
            )

        except ValueError as ex:
            return [
                tr("Y from XML: {y:.3f}", y=node_data.y),
                "",
                tr("Heightmap lookup not possible:"),
                str(ex),
            ]

        height_difference = height_sample.height - node_data.y

        return [
            tr("Y from XML: {y:.3f}", y=node_data.y),
            tr("Y from heightmap: {y:.3f}", y=height_sample.height),
            tr("Difference: {difference:+.3f}", difference=height_difference),
            "",
            "Heightmap",
            (f"Pixel: {height_sample.pixel_x}, {height_sample.pixel_y}"),
            tr("Raw value: {value}", value=height_sample.raw_value),
        ]
