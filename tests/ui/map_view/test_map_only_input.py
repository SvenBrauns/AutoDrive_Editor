import pytest
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QKeyEvent, QMouseEvent, QShortcutEvent
from PySide6.QtWidgets import QDialog

from autodrive_editor.ui.map_view.map_only_input import MapOnlyInput


def mouse_press():
    return QMouseEvent(
        QEvent.Type.MouseButtonPress,
        QPointF(5, 5),
        QPointF(5, 5),
        Qt.LeftButton,
        Qt.LeftButton,
        Qt.NoModifier,
    )


def key_press():
    return QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Delete, Qt.NoModifier)


@pytest.fixture
def input_filter(window):
    return MapOnlyInput(window, window.view)


def test_mouse_on_the_map_gets_through(window, input_filter):
    assert not input_filter.eventFilter(window.view.viewport(), mouse_press())


def test_keys_and_other_widgets_are_held_back(window, input_filter):
    assert input_filter.eventFilter(window.view, key_press())
    assert input_filter.eventFilter(window.status, mouse_press())
    assert input_filter.eventFilter(window, QEvent(QEvent.Type.Close))


def test_shortcuts_of_the_window_are_held_back(window, input_filter):
    event = QShortcutEvent(window.actions.save_xml_action.shortcut(), 0)

    assert input_filter.eventFilter(window.actions.save_xml_action, event)


def test_other_windows_are_not_affected(window, input_filter):
    dialog = QDialog(window)

    assert not input_filter.eventFilter(dialog, key_press())
    assert not input_filter.eventFilter(dialog, QEvent(QEvent.Type.Close))
    assert not input_filter.eventFilter(window.view, QEvent(QEvent.Type.Paint))


def test_map_keys_reach_the_map_before_window_shortcuts(window):
    input_filter = MapOnlyInput(window, window.view, map_keys={Qt.Key_Return})
    enter = QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Return, Qt.NoModifier)
    override = QKeyEvent(QEvent.Type.ShortcutOverride, Qt.Key_Return, Qt.NoModifier)
    override.ignore()

    assert not input_filter.eventFilter(window.view, enter)
    assert input_filter.eventFilter(window.view, override) and override.isAccepted()
    assert input_filter.eventFilter(window.view, key_press())
    assert input_filter.eventFilter(window.status, enter)
