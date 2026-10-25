"""Send real mouse and key events to the map view in tests."""

from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QKeyEvent, QMouseEvent
from PySide6.QtWidgets import QApplication


def view_pos(window, x, z) -> QPoint:
    return window.view.mapFromScene(QPointF(x, z))


def send_mouse(window, event_type, pos, button, buttons, modifiers=Qt.NoModifier):
    viewport = window.view.viewport()
    event = QMouseEvent(
        event_type, QPointF(pos), QPointF(viewport.mapToGlobal(pos)),
        button, buttons, modifiers
    )
    QApplication.sendEvent(viewport, event)


def click(window, pos, button=Qt.LeftButton, modifiers=Qt.NoModifier):
    send_mouse(window, QEvent.MouseButtonPress, pos, button, button, modifiers)
    send_mouse(window, QEvent.MouseButtonRelease, pos, button, Qt.NoButton, modifiers)


def drag(window, start, end, button=Qt.LeftButton, steps=5,
         modifiers=Qt.NoModifier, release=True):
    send_mouse(window, QEvent.MouseButtonPress, start, button, button, modifiers)

    for step in range(1, steps + 1):
        pos = start + (end - start) * step / steps
        send_mouse(window, QEvent.MouseMove, pos, Qt.NoButton, button, modifiers)

    if release:
        send_mouse(window, QEvent.MouseButtonRelease, end, button, Qt.NoButton, modifiers)


def hover(window, pos):
    send_mouse(window, QEvent.MouseMove, pos, Qt.NoButton, Qt.NoButton)


def press_escape(window):
    QApplication.sendEvent(window.view, QKeyEvent(QEvent.KeyPress, Qt.Key_Escape, Qt.NoModifier))


def cursor_shape(window):
    return window.view.viewport().cursor().shape()
