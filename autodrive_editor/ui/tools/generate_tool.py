from collections.abc import Callable
from enum import Enum

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QMouseEvent

from autodrive_editor.i18n import tr
from autodrive_editor.ui.tools.map_tool import MapTool


class GenerateTask(Enum):
    ROUTE = "route"
    JUNCTION = "junction"
    PARKING_SPOTS = "parking_spots"
    STATIONS = "stations"

    @property
    def display_name(self) -> str:
        return {
            GenerateTask.ROUTE: tr("Route"),
            GenerateTask.JUNCTION: tr("Junction"),
            GenerateTask.PARKING_SPOTS: tr("Parking spots"),
            GenerateTask.STATIONS: tr("Stations"),
        }[self]


class GenerateTool(MapTool):
    """One tool for all generators: the mouse goes to the tool of the chosen task. Selecting it
    starts planning mode, as everything generated goes into a plan first. A click or confirm
    starts it again if the plan was applied or discarded meanwhile."""

    def __init__(
        self, view, tools: dict[GenerateTask, MapTool], start_planning: Callable[[], None]
    ):
        super().__init__(view)

        self.tools = tools
        self.task = GenerateTask.ROUTE
        self._start_planning = start_planning
        self._active = False

    @property
    def current(self) -> MapTool:
        return self.tools[self.task]

    @property
    def RIGHT_CLICK_CANCELS(self) -> bool:  # noqa: N802 - read by MapView like the class constant
        return self.current.RIGHT_CLICK_CANCELS

    def set_task(self, task: GenerateTask):
        if task == self.task:
            return

        if self._active:
            self.current.deactivate()

        self.task = task

        if self._active:
            self.current.activate()

    def activate(self):
        self._active = True
        self._start_planning()
        self.current.activate()

    def deactivate(self):
        self._active = False
        self.current.deactivate()

    def mouse_press(self, event: QMouseEvent) -> bool:
        self._start_planning()
        return self.current.mouse_press(event)

    def mouse_move(self, event: QMouseEvent) -> bool:
        return self.current.mouse_move(event)

    def mouse_release(self, event: QMouseEvent) -> bool:
        return self.current.mouse_release(event)

    def mouse_leave(self):
        self.current.mouse_leave()

    def cancel(self) -> bool:
        return self.current.cancel()

    def confirm(self) -> bool:
        self._start_planning()
        return self.current.confirm()

    def remove_last(self) -> bool:
        return self.current.remove_last()

    def status_hint(self) -> str | None:
        return self.current.status_hint()

    def cursor_at(self, view_position: QPoint) -> Qt.CursorShape:
        return self.current.cursor_at(view_position)
