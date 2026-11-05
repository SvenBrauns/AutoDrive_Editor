"""The pointer position in the status bar and the scale bar."""

import re

import pytest
from mouse_helpers import hover, view_pos
from PySide6.QtCore import QEvent
from PySide6.QtWidgets import QApplication


def test_the_status_bar_shows_the_map_position_under_the_pointer(zoomed_window):
    hover(zoomed_window, view_pos(zoomed_window, 10, -5))

    numbers = [float(n) for n in re.findall(r"-?\d+\.\d", zoomed_window.pointer_position.text())]
    assert numbers == pytest.approx([10, -5], abs=0.3)

    QApplication.sendEvent(zoomed_window.view, QEvent(QEvent.Leave))

    assert zoomed_window.pointer_position.text() == ""


def test_the_scale_bar_can_be_hidden_and_stays_hidden(zoomed_window):
    assert zoomed_window.view.scale_bar_visible

    zoomed_window.actions.show_actions["scale_bar"].setChecked(False)

    assert not zoomed_window.view.scale_bar_visible
    assert not zoomed_window.settings.visibility.scale_bar
