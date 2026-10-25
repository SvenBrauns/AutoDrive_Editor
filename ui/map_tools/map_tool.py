from __future__ import annotations

from typing import TYPE_CHECKING

import shiboken6

from PySide6.QtCore import (
    QPoint,
    Qt
)
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication

if TYPE_CHECKING:
    from ui.map_view import MapView


def is_alive_in_scene(item, scene) -> bool:
    """True if a tool's overlay item still exists in the scene.
    Loading data clears the scene, which deletes such items."""

    return (
        item is not None
        and shiboken6.isValid(item)
        and item.scene() is scene
    )


class DragGesture:
    """Tracks one pressed mouse button and whether it has moved far
    enough to count as a drag."""

    def __init__(self):
        self.reset()

    @property
    def is_pressed(self) -> bool:
        return self.button != Qt.NoButton

    def press(
        self,
        button: Qt.MouseButton,
        position: QPoint
    ):
        self.button = button
        self.is_dragging = False

        self.press_position = QPoint(
            position
        )

        self.last_position = QPoint(
            position
        )

    def move(
        self,
        position: QPoint
    ) -> QPoint | None:
        """Returns the movement since the last call once the drag
        threshold is reached, otherwise None. The move that crosses
        the threshold returns a zero movement."""

        if not self.is_pressed:
            return None

        if not self.is_dragging:
            distance = (
                position
                - self.press_position
            ).manhattanLength()

            if distance < QApplication.startDragDistance():
                return None

            self.is_dragging = True

            self.last_position = QPoint(
                position
            )

            return QPoint()

        movement = (
            position
            - self.last_position
        )

        self.last_position = QPoint(
            position
        )

        return movement

    def reset(self):
        self.button = Qt.NoButton
        self.is_dragging = False
        self.press_position = QPoint()
        self.last_position = QPoint()


class MapTool:
    """Mouse handling of one map tool.

    MapView forwards left and right mouse buttons, hover moves and Esc
    to the active tool. Zooming with the wheel and rotating with the
    middle button work the same for every tool and stay in MapView.

    The default behaviour pans the map by left dragging. Tools override
    the mouse methods for their own gestures and fall back to the
    panning helpers where the map should still move.
    """

    def __init__(
        self,
        view: MapView
    ):
        self.view = view
        self._pan = DragGesture()

    def activate(self):
        pass

    def deactivate(self):
        self.cancel()
        self._pan.reset()

    def mouse_press(
        self,
        event: QMouseEvent
    ) -> bool:
        if event.button() != Qt.LeftButton:
            return False

        self._begin_pan(
            event
        )

        return True

    def mouse_move(
        self,
        event: QMouseEvent
    ) -> bool:
        return self._continue_pan(
            event
        )

    def mouse_release(
        self,
        event: QMouseEvent
    ) -> bool:
        if event.button() != Qt.LeftButton:
            return False

        self._end_pan()

        return True

    def cancel(self) -> bool:
        """Called on Esc. Returns True if something was cancelled."""

        return False

    def status_hint(self) -> str | None:
        """Optional hint shown in the status bar when the tool is
        selected, e.g. what has to be done first."""

        return None

    def cursor_at(
        self,
        view_position: QPoint
    ) -> Qt.CursorShape:
        if self._pan.is_dragging:
            return Qt.ClosedHandCursor

        return Qt.OpenHandCursor

    def _begin_pan(
        self,
        event: QMouseEvent
    ):
        self._pan.press(
            Qt.LeftButton,
            event.position().toPoint()
        )

    def _continue_pan(
        self,
        event: QMouseEvent
    ) -> bool:
        """Pans while the left button is held. Returns True while a
        pan gesture is in progress."""

        if not (
            self._pan.is_pressed
            and event.buttons() & Qt.LeftButton
        ):
            return False

        movement = self._pan.move(
            event.position().toPoint()
        )

        if movement is not None:
            self.view.pan_by(
                movement
            )

        return True

    def _end_pan(self) -> bool:
        """Ends the pan gesture. Returns True if the map was dragged,
        False for a plain click."""

        was_dragging = self._pan.is_dragging

        self._pan.reset()

        return was_dragging
