from collections.abc import Callable

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QMouseEvent, QPainterPath

from autodrive_editor.file_io.savegame_sheds import IndoorArea
from autodrive_editor.ui.tools.station_pick_tool import StationPickTool


class AreaPickTool(StationPickTool):
    """Picks sheds or bunker silos: a click opens the area at the pointer, Shift-click adds or
    removes an area from the pick (if may_add allows it), Enter or a click on a picked area opens
    the pick, right dragging the areas in a box (Shift: a lasso). Esc drops the pick. Left
    dragging pans."""

    def __init__(
        self,
        view,
        area_at: Callable[[QPoint], IndoorArea | None],
        areas_in: Callable[[QPainterPath], list[IndoorArea]],
        create: Callable[[list[IndoorArea]], bool],
        show_picked: Callable[[list[IndoorArea]], None],
        hint: Callable[[], str],
        hover_text: Callable[[QPoint], str],
        may_add: Callable[[list[IndoorArea], IndoorArea], bool] = lambda picked, area: True,
    ):
        super().__init__(
            view,
            self._clicked,
            lambda path: self._open(areas_in(path)),
            hint,
            is_target=lambda view_position: area_at(view_position) is not None,
            hover_text=hover_text,
        )

        self._area_at = area_at
        self._create = create
        self._show_picked = show_picked
        self._may_add = may_add
        self.picked: list[IndoorArea] = []
        self._shift = False

    def deactivate(self):
        super().deactivate()
        self._set_picked([])

    def mouse_release(self, event: QMouseEvent) -> bool:
        self._shift = bool(event.modifiers() & Qt.ShiftModifier)
        return super().mouse_release(event)

    def _clicked(self, view_position: QPoint) -> bool:
        area = self._area_at(view_position)

        if area is None:
            return False

        if self._shift:
            if area in self.picked:
                self._set_picked([other for other in self.picked if other != area])
            elif self._may_add(self.picked, area):
                self._set_picked(self.picked + [area])

            return True

        return self._open(self.picked if area in self.picked else [area])

    def confirm(self) -> bool:
        return bool(self.picked) and self._open(self.picked)

    def cancel(self) -> bool:
        if super().cancel():
            return True

        if not self.picked:
            return False

        self._set_picked([])
        return True

    def _open(self, areas: list[IndoorArea]) -> bool:
        if not areas:
            return False

        self._set_picked(areas)

        try:
            return self._create(areas)
        finally:
            self._set_picked([])

    def _set_picked(self, areas: list[IndoorArea]):
        self.picked = areas
        self._show_picked(areas)
