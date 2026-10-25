from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QMouseEvent

from autodrive_editor.selection.selection_coordinator import SelectionCoordinator
from autodrive_editor.ui.map_view.area_selection import AreaSelectionController
from autodrive_editor.ui.tools.map_tool import MapTool


class SelectTool(MapTool):
    """Left click selects a node, Ctrl + left click toggles it.
    Right dragging selects all nodes in a box, Shift + right dragging
    in a freehand lasso. Left dragging pans."""

    # The right button draws the selection box.
    RIGHT_CLICK_CANCELS = False

    def __init__(self, view, selection_coordinator: SelectionCoordinator):
        super().__init__(view)

        self.selection_coordinator = selection_coordinator

        self._area_selection = AreaSelectionController(view=view, parent=view)

        self._area_selection.area_requested.connect(selection_coordinator.handle_area)

        self._area_selection.area_preview_requested.connect(
            selection_coordinator.handle_area_preview
        )

        self._area_selection.area_preview_cleared.connect(selection_coordinator.clear_area_preview)

        self._right_button_pressed = False

    def deactivate(self):
        super().deactivate()
        self._cancel_area_selection()

    def mouse_press(self, event: QMouseEvent) -> bool:
        if event.button() == Qt.RightButton:
            self._right_button_pressed = True

            self._area_selection.begin(
                event.position().toPoint(), lasso=bool(event.modifiers() & Qt.ShiftModifier)
            )

            return True

        return super().mouse_press(event)

    def mouse_move(self, event: QMouseEvent) -> bool:
        if self._right_button_pressed and event.buttons() & Qt.RightButton:
            self._area_selection.handle_drag(
                current_position=event.position().toPoint(), modifiers=event.modifiers()
            )

            return True

        return super().mouse_move(event)

    def mouse_release(self, event: QMouseEvent) -> bool:
        if event.button() == Qt.RightButton and self._right_button_pressed:
            self._right_button_pressed = False

            self._area_selection.finish(event.modifiers())

            return True

        if event.button() != Qt.LeftButton:
            return False

        if not self._end_pan():
            self.selection_coordinator.handle_click(event.position().toPoint(), event.modifiers())

        return True

    def cancel(self) -> bool:
        if not self._right_button_pressed:
            return False

        self._cancel_area_selection()

        return True

    def status_hint(self) -> str | None:
        return (
            "Klick wählt eine Node, Strg+Klick schaltet um, Rechtsziehen wählt einen Bereich, "
            "Umschalt+Rechtsziehen zeichnet ein Lasso"
        )

    def cursor_at(self, view_position: QPoint) -> Qt.CursorShape:
        if self._area_selection.drag_active:
            return Qt.CrossCursor

        if self._pan.is_dragging:
            return Qt.ClosedHandCursor

        if self.view.has_selectable_item_at(view_position):
            return Qt.ArrowCursor

        return Qt.OpenHandCursor

    def _cancel_area_selection(self):
        self._right_button_pressed = False
        self._area_selection.cancel()
