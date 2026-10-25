from ui.map_tools.map_tool import MapTool


class NavigateTool(MapTool):
    """Left dragging pans the map. Clicks do nothing."""

    def status_hint(self) -> str | None:
        return "Linkes Ziehen verschiebt die Karte, mittleres Ziehen dreht sie"
