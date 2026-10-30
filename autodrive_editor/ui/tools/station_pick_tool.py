from collections.abc import Callable

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QMouseEvent, QPainterPath

from autodrive_editor.ui.map_view.area_selection import AreaSelectionController
from autodrive_editor.ui.tools.node_click_tool import NodeClickTool


class StationPickTool(NodeClickTool):
    """Picks station buildings: a click picks the building at the pointer, right dragging all
    stops in a box (Shift: a lasso). Left dragging pans."""

    # The right button draws the box.
    RIGHT_CLICK_CANCELS = False

    def __init__(
        self,
        view,
        click: Callable[[QPoint], bool],
        pick_area: Callable[[QPainterPath], bool],
        hint: str | Callable[[], str],
        is_target: Callable[[QPoint], bool],
        hover_text: Callable[[QPoint], str],
    ):
        super().__init__(view, click, hint, is_target=is_target, hover_text=hover_text)

        self._area = AreaSelectionController(view=view, parent=view)
        self._area.area_requested.connect(lambda path, modifiers: pick_area(path))
        self._right_button_pressed = False

    def deactivate(self):
        super().deactivate()
        self._cancel_area()

    def mouse_press(self, event: QMouseEvent) -> bool:
        if event.button() == Qt.RightButton:
            self._right_button_pressed = True
            self._area.begin(
                event.position().toPoint(), lasso=bool(event.modifiers() & Qt.ShiftModifier)
            )
            return True

        return super().mouse_press(event)

    def mouse_move(self, event: QMouseEvent) -> bool:
        if self._right_button_pressed and event.buttons() & Qt.RightButton:
            self._area.handle_drag(event.position().toPoint(), event.modifiers())
            return True

        return super().mouse_move(event)

    def mouse_release(self, event: QMouseEvent) -> bool:
        if event.button() == Qt.RightButton and self._right_button_pressed:
            self._right_button_pressed = False
            self._area.finish(event.modifiers())
            return True

        return super().mouse_release(event)

    def cancel(self) -> bool:
        if not self._right_button_pressed:
            return False

        self._cancel_area()
        return True

    def cursor_at(self, view_position: QPoint) -> Qt.CursorShape:
        if self._area.drag_active:
            return Qt.CrossCursor

        return super().cursor_at(view_position)

    def _cancel_area(self):
        self._right_button_pressed = False
        self._area.cancel()
