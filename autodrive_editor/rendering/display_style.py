from dataclasses import dataclass


@dataclass(frozen=True)
class DisplayStyle:
    """Sizes, colors and layers of everything drawn on the map.

    Sizes are in metres on the map and grow with the zoom, but stay between a minimum and maximum
    size on screen (in pixels). The same rule applies at every zoom level, so the map changes
    smoothly instead of switching between an overview and a detail view.
    """

    node_diameter: float = 2.0
    node_max_px: float = 16.0
    node_border_width: float = 0.2

    # Nodes fade in while their diameter on screen grows from start to end.
    node_fade_start_px: float = 1.5
    node_fade_end_px: float = 4.0

    # Selected nodes are drawn at least this big, at every zoom level.
    selected_node_min_px: float = 5.0
    selected_node_ring_width: float = 0.3

    # Node IDs, when switched on, are shown from this zoom on.
    node_id_min_zoom: float = 4.0

    connection_width: float = 0.35
    connection_min_px: float = 1.0
    connection_max_px: float = 3.0

    regular_connection_color: tuple[int, int, int] = (0, 230, 0)
    dual_connection_color: tuple[int, int, int] = (40, 110, 255)
    reverse_connection_color: tuple[int, int, int] = (100, 220, 255)
    # Connections into subprio nodes.
    subprio_connection_color: tuple[int, int, int] = (255, 140, 0)

    # Arrows sit in the middle of one-way connections. They shrink on short connections and are
    # left out once they would be smaller than arrow_min_px.
    arrow_length: float = 2.5
    arrow_min_px: float = 6.0
    arrow_max_px: float = 14.0

    # Height of the marker icon.
    marker_size: float = 8.0
    marker_min_px: float = 14.0
    marker_max_px: float = 26.0
    # Marker names fade in just below this zoom and are fully shown from it on.
    marker_name_min_zoom: float = 1.0

    connection_z: float = -10.0
    node_z: float = 0.0
    marker_z: float = 10.0
    selected_node_z: float = 110.0
