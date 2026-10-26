from autodrive_editor.i18n import tr
from autodrive_editor.ui.tools.map_tool import MapTool


class NavigateTool(MapTool):
    """Left dragging pans the map. Clicks do nothing."""

    def status_hint(self) -> str | None:
        return tr("Left-drag moves the map, middle-drag rotates it")
