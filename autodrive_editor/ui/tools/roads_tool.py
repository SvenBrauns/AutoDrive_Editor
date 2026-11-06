from collections.abc import Callable

from PySide6.QtCore import QPoint
from PySide6.QtGui import QPainterPath

from autodrive_editor.ui.tools.station_pick_tool import StationPickTool


class RoadsTool(StationPickTool):
    """The Roads task of the Generate tool: shown(True) when it becomes active (the map's
    traffic lanes are shown), shown(False) when it ends. A click builds the road under the
    pointer, right dragging the roads in a box, Enter the whole map, each as the mode allows.
    Left dragging pans."""

    def __init__(
        self,
        view,
        click: Callable[[QPoint], bool],
        pick_area: Callable[[QPainterPath], bool],
        create: Callable[[], bool],
        shown: Callable[[bool], None],
        hint: Callable[[], str],
        is_target: Callable[[QPoint], bool],
    ):
        super().__init__(view, click, pick_area, hint, is_target, hover_text=lambda position: "")

        self._create = create
        self._shown = shown

    def activate(self):
        super().activate()
        self._shown(True)

    def deactivate(self):
        super().deactivate()
        self._shown(False)

    def confirm(self) -> bool:
        return self._create()
