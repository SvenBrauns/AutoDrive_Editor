from autodrive.models import (
    AutoDriveData,
    NodeData
)
from map.background_manager import BackgroundManager
from map.heightmap_manager import HeightmapManager


class NodeInfoFormatter:

    def __init__(
        self,
        background_manager: BackgroundManager,
        heightmap_manager: HeightmapManager
    ):
        self.background_manager = background_manager
        self.heightmap_manager = heightmap_manager

    def format_node_info(
        self,
        node_data: NodeData,
        autodrive_data: AutoDriveData | None
    ) -> str:
        node_type = self._get_node_type(
            node_data
        )

        marker_lines = self._get_marker_lines(
            node_data,
            autodrive_data
        )

        heightmap_lines = self._get_heightmap_lines(
            node_data
        )

        info_lines = [
            f"Node {node_data.node_id}",
            "",
            f"Typ: {node_type}",
            "",
            "Koordinaten",
            f"X: {node_data.x:.3f}",
            *heightmap_lines,
            f"Z: {node_data.z:.3f}"
        ]

        if marker_lines:
            info_lines.extend(
                [
                    "",
                    "Marker",
                    *marker_lines
                ]
            )

        return "\n".join(
            info_lines
        )

    @staticmethod
    def _get_node_type(
        node_data: NodeData
    ) -> str:
        if node_data.is_regular:
            return "Regular Node"

        return "Subprio Node"

    @staticmethod
    def _get_marker_lines(
        node_data: NodeData,
        autodrive_data: AutoDriveData | None
    ) -> list[str]:
        if autodrive_data is None:
            return []

        marker_data = autodrive_data.get_marker(
            node_data.node_id
        )

        if marker_data is None:
            return []

        return [
            f"Name: {marker_data.name}",
            f"Gruppe: {marker_data.group}"
        ]

    def _get_heightmap_lines(
        self,
        node_data: NodeData
    ) -> list[str]:
        if not self.heightmap_manager.has_heightmap():
            return [
                f"Y: {node_data.y:.3f}"
            ]

        try:
            height_sample = (
                self.heightmap_manager.get_height_at(
                    world_x=node_data.x,
                    world_z=node_data.z,
                    map_scale=(
                        self.background_manager.map_scale
                    )
                )
            )

        except ValueError as ex:
            return [
                f"Y laut XML: {node_data.y:.3f}",
                "",
                "Heightmap-Auswertung nicht möglich:",
                str(ex)
            ]

        height_difference = (
            height_sample.height
            - node_data.y
        )

        return [
            f"Y laut XML: {node_data.y:.3f}",
            f"Y laut Heightmap: {height_sample.height:.3f}",
            f"Abweichung: {height_difference:+.3f}",
            "",
            "Heightmap",
            (
                f"Pixel: "
                f"{height_sample.pixel_x}, "
                f"{height_sample.pixel_y}"
            ),
            f"Rohwert: {height_sample.raw_value}"
        ]