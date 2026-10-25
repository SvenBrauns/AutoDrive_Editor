from collections.abc import Callable

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QMouseEvent

from autodrive_editor.ui.tools.map_tool import MapTool


class NodeClickTool(MapTool):
    """A tool that does one thing when a node is clicked, e.g. the marker
    tools. Left dragging pans the map. Esc and right-click call cancel
    if the tool has a step to cancel.

    The cursor shows a pointing hand over a node, or over whatever
    is_target reports for tools that click something else."""

    def __init__(
        self,
        view,
        click: Callable[[QPoint], bool],
        hint: str | Callable[[], str],
        cancel: Callable[[], bool] | None = None,
        is_target: Callable[[QPoint], bool] | None = None,
    ):
        super().__init__(view)

        self._click = click
        self._hint = hint
        self._cancel = cancel
        self._is_target = is_target or view.has_selectable_item_at

    def mouse_release(self, event: QMouseEvent) -> bool:
        if event.button() != Qt.LeftButton:
            return False

        # Only a click acts. Releasing after a pan does nothing.
        if not self._end_pan():
            self._click(event.position().toPoint())

        return True

    def cancel(self) -> bool:
        return self._cancel() if self._cancel is not None else False

    def status_hint(self) -> str | None:
        return self._hint() if callable(self._hint) else self._hint

    def cursor_at(self, view_position: QPoint) -> Qt.CursorShape:
        if self._pan.is_dragging:
            return Qt.ClosedHandCursor

        if self._is_target(view_position):
            return Qt.PointingHandCursor

        return Qt.OpenHandCursor
