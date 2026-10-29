from collections.abc import Callable

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QMouseEvent, QPalette
from PySide6.QtWidgets import QFrame, QLabel, QToolTip

from autodrive_editor.ui.tools.map_tool import MapTool

# Distance of the hover text from the pointer, in pixels.
HOVER_TEXT_OFFSET = QPoint(14, 18)


class NodeClickTool(MapTool):
    """A tool that does one thing when a node is clicked, e.g. the marker
    tools. Left dragging pans the map. Esc and right-click call cancel
    if the tool has a step to cancel.

    The cursor shows a pointing hand over a node, or over whatever
    is_target reports for tools that click something else. hover_text, if given, is shown next
    to the pointer while it is not empty."""

    def __init__(
        self,
        view,
        click: Callable[[QPoint], bool],
        hint: str | Callable[[], str],
        cancel: Callable[[], bool] | None = None,
        is_target: Callable[[QPoint], bool] | None = None,
        hover_text: Callable[[QPoint], str] | None = None,
    ):
        super().__init__(view)

        self._click = click
        self._hint = hint
        self._cancel = cancel
        self._is_target = is_target or view.has_node_at
        self._hover_text = hover_text
        # A label of its own, since a QToolTip is hidden and faded by Qt's timers.
        self._hover_label: QLabel | None = None

    def deactivate(self):
        super().deactivate()
        self._show_hover_text(QPoint(), "")

    def mouse_move(self, event: QMouseEvent) -> bool:
        handled = super().mouse_move(event)

        if self._hover_text is not None:
            position = event.position().toPoint()
            self._show_hover_text(
                position, "" if self._pan.is_dragging else self._hover_text(position)
            )

        return handled

    def mouse_leave(self):
        self._show_hover_text(QPoint(), "")

    def _show_hover_text(self, position: QPoint, text: str):
        label = self._hover_label

        if not text:
            if label is not None:
                label.hide()
            return

        viewport = self.view.viewport()

        if label is None:
            label = self._hover_label = QLabel(viewport)
            label.setAttribute(Qt.WA_TransparentForMouseEvents)
            label.setPalette(QToolTip.palette())
            label.setFont(QToolTip.font())
            label.setBackgroundRole(QPalette.ToolTipBase)
            label.setForegroundRole(QPalette.ToolTipText)
            label.setAutoFillBackground(True)
            label.setFrameShape(QFrame.Box)
            label.setMargin(3)

        label.setText(text)
        label.adjustSize()

        # Beside the pointer, on its other side near the right and bottom edge.
        x, y = position.x() + HOVER_TEXT_OFFSET.x(), position.y() + HOVER_TEXT_OFFSET.y()

        if x + label.width() > viewport.width():
            x = position.x() - HOVER_TEXT_OFFSET.x() - label.width()

        if y + label.height() > viewport.height():
            y = position.y() - HOVER_TEXT_OFFSET.y() - label.height()

        label.move(x, y)
        label.show()
        label.raise_()

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
