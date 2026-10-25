from dataclasses import dataclass


@dataclass(frozen=True)
class DisplayStyle:
    node_diameter: float = 2.0
    node_border_width: float = 0.2

    selected_node_ring_width: float = 0.2

    marker_scale: float = 0.05
    selected_marker_scale: float = 0.06

    marker_anchor_x: float = 0.5
    marker_anchor_y: float = 1.0
    marker_node_gap: float = 0.5
    regular_connection_color: tuple[int, int, int] = (0, 255, 0)

    dual_connection_color: tuple[int, int, int] = (0, 0, 255)

    reverse_connection_color: tuple[int, int, int] = (100, 220, 255)
    connection_width: float = 0.8
    selected_connection_width: float = 1.4

    node_min_zoom: float = 1.0
    marker_min_zoom: float = 1.0

    normal_connection_z: float = -10.0
    normal_node_z: float = 0.0
    normal_marker_z: float = 10.0

    selected_connection_z: float = 100.0
    selected_node_z: float = 110.0
    selected_marker_z: float = 120.0

    detailed_connection_width: float = 0.25
    connection_detail_min_zoom: float = 1.0

    arrow_length: float = 1.5
    arrow_width: float = 1.2
