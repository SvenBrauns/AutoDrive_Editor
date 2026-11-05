"""Select all and whole road pieces: double-click in the Select tool and the Edit menu."""

import pytest
from mouse_helpers import click, send_mouse, view_pos
from PySide6.QtCore import QEvent, Qt

from autodrive_editor.ui.tools.interaction_mode import InteractionMode


@pytest.fixture
def select_mode(zoomed_window):
    zoomed_window.set_interaction_mode(InteractionMode.SELECT)
    return zoomed_window


def double_click(window, pos, modifiers=Qt.NoModifier):
    click(window, pos, modifiers=modifiers)
    send_mouse(window, QEvent.MouseButtonDblClick, pos, Qt.LeftButton, Qt.LeftButton, modifiers)
    send_mouse(window, QEvent.MouseButtonRelease, pos, Qt.LeftButton, Qt.NoButton, modifiers)


def selected(window):
    return window.node_selection.selected_node_ids


def test_double_click_on_a_node_selects_its_road_piece(select_mode):
    double_click(select_mode, view_pos(select_mode, 20, 0))

    assert selected(select_mode) == {1, 2, 3}


def test_double_click_on_a_connection_selects_its_road_piece(select_mode):
    double_click(select_mode, view_pos(select_mode, 15, 0))

    assert selected(select_mode) == {1, 2, 3}


def test_select_all_and_select_road_piece_in_the_edit_menu(select_mode):
    select_mode.actions.select_all_action.trigger()
    assert selected(select_mode) == {1, 2, 3}

    click(select_mode, view_pos(select_mode, 10, 0))
    select_mode.actions.select_road_piece_action.trigger()
    assert selected(select_mode) == {1, 2, 3}
