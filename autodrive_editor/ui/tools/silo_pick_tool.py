from collections.abc import Callable

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QMouseEvent, QPainterPath

from autodrive_editor.file_io.savegame_sheds import IndoorArea
from autodrive_editor.ui.tools.station_pick_tool import StationPickTool


class SiloPickTool(StationPickTool):
    """Picks bunker silos: a click opens the silo at the pointer, Shift-click adds or removes a
    silo from the pick, Enter or a click on a picked silo opens the pick, right dragging the
    silos in a box (Shift: a lasso). Esc drops the pick. Left dragging pans."""

    def __init__(
        self,
        view,
        silo_at: Callable[[QPoint], IndoorArea | None],
        silos_in: Callable[[QPainterPath], list[IndoorArea]],
        create: Callable[[list[IndoorArea]], bool],
        show_picked: Callable[[list[IndoorArea]], None],
        hint: Callable[[], str],
        hover_text: Callable[[QPoint], str],
    ):
        super().__init__(
            view,
            self._clicked,
            lambda path: self._open(silos_in(path)),
            hint,
            is_target=lambda view_position: silo_at(view_position) is not None,
            hover_text=hover_text,
        )

        self._silo_at = silo_at
        self._create = create
        self._show_picked = show_picked
        self.picked: list[IndoorArea] = []
        self._shift = False

    def deactivate(self):
        super().deactivate()
        self._set_picked([])

    def mouse_release(self, event: QMouseEvent) -> bool:
        self._shift = bool(event.modifiers() & Qt.ShiftModifier)
        return super().mouse_release(event)

    def _clicked(self, view_position: QPoint) -> bool:
        silo = self._silo_at(view_position)

        if silo is None:
            return False

        if self._shift:
            others = [area for area in self.picked if area != silo]
            self._set_picked(others if silo in self.picked else self.picked + [silo])
            return True

        return self._open(self.picked if silo in self.picked else [silo])

    def confirm(self) -> bool:
        return bool(self.picked) and self._open(self.picked)

    def cancel(self) -> bool:
        if super().cancel():
            return True

        if not self.picked:
            return False

        self._set_picked([])
        return True

    def _open(self, silos: list[IndoorArea]) -> bool:
        if not silos:
            return False

        self._set_picked(silos)

        try:
            return self._create(silos)
        finally:
            self._set_picked([])

    def _set_picked(self, silos: list[IndoorArea]):
        self.picked = silos
        self._show_picked(silos)
