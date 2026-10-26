"""Reversing connection directions."""

import pytest
from mouse_helpers import click, cursor_shape, hover, view_pos
from PySide6.QtCore import Qt

from autodrive_editor.editing.commands.reverse_connections import ReverseConnectionsCommand
from autodrive_editor.model.autodrive_data import AutoDriveData, NodeData
from autodrive_editor.model.connections import ConnectionType, get_connection_type
from autodrive_editor.ui.tools.interaction_mode import InteractionMode


def connection(data, source_id, target_id):
    source, target = data.nodes[source_id], data.nodes[target_id]
    return get_connection_type(source, target) if target_id in source.outgoing else None


# --- command ------------------------------------------------------------------


@pytest.fixture
def data():
    """1 -> 2 regular, 2 -> 3 reverse, 3 <-> 4 dual."""

    autodrive_data = AutoDriveData()
    autodrive_data.add_node(NodeData(1, 0, 0, 0, outgoing={2}))
    autodrive_data.add_node(NodeData(2, 10, 0, 0, incoming={1}, outgoing={3}))
    autodrive_data.add_node(NodeData(3, 20, 0, 0, incoming={4}, outgoing={4}))
    autodrive_data.add_node(NodeData(4, 30, 0, 0, incoming={3}, outgoing={3}))
    return autodrive_data


def test_regular_and_reverse_keep_their_type(data):
    ReverseConnectionsCommand(data, {(1, 2), (3, 2)}).apply()

    assert connection(data, 1, 2) is None
    assert connection(data, 2, 1) == ConnectionType.REGULAR
    assert connection(data, 2, 3) is None
    assert connection(data, 3, 2) == ConnectionType.REVERSE
    assert data.validate_connections() == []


def test_undo_restores_the_directions(data):
    command = ReverseConnectionsCommand(data, {(1, 2), (2, 3)})

    command.apply()
    command.revert()

    assert connection(data, 1, 2) == ConnectionType.REGULAR
    assert connection(data, 2, 3) == ConnectionType.REVERSE


def test_command_text_counts_connections(data):
    assert ReverseConnectionsCommand(data, {(1, 2)}).text() == "Reverse direction"
    assert ReverseConnectionsCommand(data, {(1, 2), (2, 3)}).text() == "Reverse 2 directions"


# --- tool ------------------------------------------------------------------------


@pytest.fixture
def reverse_window(window, write_xml, qapp):
    """1 (x=0) -> 2 (x=10) regular, 2 <-> 3 (x=20) dual, 3 -> 4 (x=30) regular."""

    path = write_xml(
        x="0;10;20;30",
        y="0;0;0;0",
        z="0;0;0;0",
        out="2;3;2,4;",
        incoming=";1,3;2;3",
        flags="0;0;0;0",
    )
    window.project_coordinator.load_xml_file(path)
    window.view.set_zoom_level(4.0)
    window.view.centerOn(15, 0)
    qapp.processEvents()
    window.set_interaction_mode(InteractionMode.REVERSE_DIRECTION)
    window.data = window.project_coordinator.autodrive_data
    return window


def test_click_on_a_connection_reverses_it(reverse_window):
    click(reverse_window, view_pos(reverse_window, 5, 0))

    assert connection(reverse_window.data, 2, 1) == ConnectionType.REGULAR
    assert reverse_window.status.text() == "Direction reversed"


def test_click_slightly_next_to_the_line_still_hits(reverse_window):
    pos = view_pos(reverse_window, 5, 0)
    pos.setY(pos.y() + 4)  # 4 px below the line

    click(reverse_window, pos)

    assert connection(reverse_window.data, 2, 1) == ConnectionType.REGULAR


def test_click_far_from_lines_does_nothing(reverse_window):
    click(reverse_window, view_pos(reverse_window, 5, 8))

    assert not reverse_window.edit_history.can_undo


def test_dual_connection_is_not_changed(reverse_window):
    click(reverse_window, view_pos(reverse_window, 15, 0))

    assert connection(reverse_window.data, 2, 3) == ConnectionType.DUAL
    assert "Dual" in reverse_window.status.text()
    assert not reverse_window.edit_history.can_undo


def test_connection_inside_selection_reverses_the_whole_selection(reverse_window):
    reverse_window.node_selection.replace({1, 2, 3, 4})

    click(reverse_window, view_pos(reverse_window, 5, 0))

    assert connection(reverse_window.data, 2, 1) == ConnectionType.REGULAR
    assert connection(reverse_window.data, 4, 3) == ConnectionType.REGULAR
    assert connection(reverse_window.data, 2, 3) == ConnectionType.DUAL
    assert reverse_window.status.text() == "2 directions reversed"

    reverse_window.edit_history.undo()
    assert connection(reverse_window.data, 1, 2) == ConnectionType.REGULAR
    assert connection(reverse_window.data, 3, 4) == ConnectionType.REGULAR


def test_connection_outside_selection_reverses_only_itself(reverse_window):
    reverse_window.node_selection.replace({3, 4})

    click(reverse_window, view_pos(reverse_window, 5, 0))

    assert connection(reverse_window.data, 2, 1) == ConnectionType.REGULAR
    assert connection(reverse_window.data, 3, 4) == ConnectionType.REGULAR


def test_cursor_shows_when_a_connection_is_hit(reverse_window):
    hover(reverse_window, view_pos(reverse_window, 5, 0))
    assert cursor_shape(reverse_window) == Qt.PointingHandCursor

    hover(reverse_window, view_pos(reverse_window, 5, 8))
    assert cursor_shape(reverse_window) == Qt.OpenHandCursor
