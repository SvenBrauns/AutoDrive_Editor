"""Entering a node position as numbers."""

import pytest
from mouse_helpers import click, view_pos

from autodrive_editor.ui.dialogs.node_position_dialog import NodePositionDialog
from autodrive_editor.ui.tools.interaction_mode import InteractionMode


@pytest.fixture
def position_window(zoomed_window):
    window = zoomed_window
    window.asked = []
    window.answer = (12.5, 3.25, -7.0)

    def ask(node):
        window.asked.append(node.node_id)
        return window.answer

    window._ask_node_position = ask
    window.set_interaction_mode(InteractionMode.EDIT_NODE_POSITION)
    window.data = window.project_coordinator.autodrive_data
    return window


def position(window, node_id):
    node = window.data.nodes[node_id]
    return node.x, node.y, node.z


def test_click_on_node_sets_the_entered_position(position_window):
    click(position_window, view_pos(position_window, 10, 0))

    assert position_window.asked == [2]
    assert position(position_window, 2) == (12.5, 3.25, -7.0)
    assert position_window.status.text() == "Position of node 2 changed"


def test_change_is_one_undo_step(position_window):
    click(position_window, view_pos(position_window, 10, 0))

    position_window.edit_history.undo()

    assert position(position_window, 2) == (10, 0, 0)


def test_selection_does_not_matter(position_window):
    position_window.node_selection.replace({1, 2, 3})

    click(position_window, view_pos(position_window, 10, 0))

    assert position(position_window, 1) == (0, 0, 0)
    assert position(position_window, 3) == (20, 0, 0)


def test_cancel_or_unchanged_values_change_nothing(position_window):
    position_window.answer = None
    click(position_window, view_pos(position_window, 10, 0))

    position_window.answer = (10, 0, 0)
    click(position_window, view_pos(position_window, 10, 0))

    assert not position_window.edit_history.can_undo


def test_click_on_empty_map_does_not_ask(position_window):
    click(position_window, view_pos(position_window, 10, 30))

    assert position_window.asked == []


def test_dialog_shows_and_returns_values(qapp):
    dialog = NodePositionDialog(7, 1.5, 2.25, -3.125)

    assert dialog.values == (1.5, 2.25, -3.125)
    assert dialog.windowTitle() == "Position of node 7"

    dialog.z_input.setValue(99.5)
    assert dialog.values == (1.5, 2.25, 99.5)
