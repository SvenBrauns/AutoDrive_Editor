"""The three "Verbinden" tools, driven by real mouse and key input."""

import pytest

from PySide6.QtCore import QPoint, QRectF, Qt

from editing.set_connection_command import CONNECTION_STATES, NO_CONNECTION, read_connection_state
from mouse_helpers import click, cursor_shape, drag, hover, press_escape, view_pos
from rendering.connection_data import ConnectionType
from ui.interaction_mode import InteractionMode

# Test network from conftest: 1 -> 2 -> 3 (regular) on z=0 at x = 0, 10, 20.

MODES = {
    ConnectionType.REGULAR: InteractionMode.CONNECT_REGULAR,
    ConnectionType.DUAL: InteractionMode.CONNECT_DUAL,
    ConnectionType.REVERSE: InteractionMode.CONNECT_REVERSE,
}

EMPTY = (5, 20)


def data(window):
    return window.project_coordinator.autodrive_data


def state(window, source, target):
    return read_connection_state(data(window), source, target)


def tool(window):
    return window.view.active_tool


def connections_between(window, a, b):
    return [
        c for c in window.scene_renderer.connection_spatial_index.get_connections_in_rect(
            QRectF(-100, -100, 200, 200)
        )
        if {c.source_id, c.target_id} == {a, b}
    ]


@pytest.fixture
def connecting(zoomed_window):
    def use(connection_type):
        zoomed_window.set_interaction_mode(MODES[connection_type])
        return zoomed_window
    return use


@pytest.mark.parametrize("connection_type", list(ConnectionType))
def test_clicking_two_nodes_connects_them(connecting, connection_type):
    window = connecting(connection_type)

    click(window, view_pos(window, 0, 0))
    click(window, view_pos(window, 20, 0))

    assert state(window, 1, 3) == CONNECTION_STATES[connection_type]
    drawn = connections_between(window, 1, 3)
    assert [c.connection_type for c in drawn] == [connection_type]


def test_chain_continues_from_last_node(connecting):
    window = connecting(ConnectionType.DUAL)

    for x in (0, 10, 20):
        click(window, view_pos(window, x, 0))

    assert state(window, 1, 2) == CONNECTION_STATES[ConnectionType.DUAL]
    assert state(window, 2, 3) == CONNECTION_STATES[ConnectionType.DUAL]
    assert window.edit_coordinator.undo_stack.count() == 2
    assert window.node_connect_coordinator.start_node.node_id == 3


def test_same_type_removes_existing_connection(connecting):
    window = connecting(ConnectionType.REGULAR)   # 1 -> 2 is regular already

    click(window, view_pos(window, 0, 0))
    click(window, view_pos(window, 10, 0))

    assert state(window, 1, 2) == NO_CONNECTION
    assert connections_between(window, 1, 2) == []
    assert window.status.text() == "Regular-Connection 1 → 2 entfernt"


def test_other_type_replaces_existing_connection(connecting):
    window = connecting(ConnectionType.REVERSE)

    click(window, view_pos(window, 0, 0))
    click(window, view_pos(window, 10, 0))

    assert state(window, 1, 2) == CONNECTION_STATES[ConnectionType.REVERSE]
    assert window.actions.undo_action.text() == "Rückgängig: Connection ändern"


def test_clicking_opposite_direction_flips_regular_connection(connecting):
    window = connecting(ConnectionType.REGULAR)

    click(window, view_pos(window, 10, 0))
    click(window, view_pos(window, 0, 0))

    assert state(window, 2, 1) == CONNECTION_STATES[ConnectionType.REGULAR]


def test_undo_restores_connection_and_drawing(connecting):
    window = connecting(ConnectionType.DUAL)
    click(window, view_pos(window, 0, 0))
    click(window, view_pos(window, 10, 0))

    window.actions.undo_action.trigger()

    assert state(window, 1, 2) == CONNECTION_STATES[ConnectionType.REGULAR]
    assert [c.connection_type for c in connections_between(window, 1, 2)] == [ConnectionType.REGULAR]


def test_click_on_empty_map_ends_chain(connecting):
    window = connecting(ConnectionType.REGULAR)
    click(window, view_pos(window, 0, 0))

    click(window, view_pos(window, *EMPTY))
    click(window, view_pos(window, 20, 0))

    assert state(window, 1, 3) == NO_CONNECTION
    assert window.node_connect_coordinator.start_node.node_id == 3


def test_escape_ends_chain(connecting):
    window = connecting(ConnectionType.REGULAR)
    click(window, view_pos(window, 0, 0))

    press_escape(window)
    click(window, view_pos(window, 20, 0))

    assert state(window, 1, 3) == NO_CONNECTION


def test_clicking_start_node_again_does_nothing(connecting):
    window = connecting(ConnectionType.REGULAR)

    click(window, view_pos(window, 0, 0))
    click(window, view_pos(window, 0, 0))

    assert window.edit_coordinator.undo_stack.count() == 0
    assert window.node_connect_coordinator.start_node.node_id == 1


def test_dragging_pans_without_connecting(connecting):
    window = connecting(ConnectionType.REGULAR)
    click(window, view_pos(window, 0, 0))
    start = view_pos(window, 20, 0)

    drag(window, start, start + QPoint(60, 0))

    assert state(window, 1, 3) == NO_CONNECTION
    assert window.node_connect_coordinator.start_node.node_id == 1


def test_preview_line_follows_mouse(connecting):
    window = connecting(ConnectionType.DUAL)
    assert tool(window).preview_line is None

    click(window, view_pos(window, 0, 0))
    hover(window, view_pos(window, 5, 20))

    line = tool(window).preview_line
    assert (line.x1(), line.y1()) == (0, 0)
    assert (line.x2(), line.y2()) == pytest.approx((5, 20), abs=0.5)
    assert cursor_shape(window) == Qt.CrossCursor

    press_escape(window)
    assert tool(window).preview_line is None


def test_switching_tool_ends_chain(connecting):
    window = connecting(ConnectionType.REGULAR)
    click(window, view_pos(window, 0, 0))

    window.set_interaction_mode(InteractionMode.CONNECT_DUAL)

    assert window.node_connect_coordinator.start_node is None


def test_chain_ends_when_start_node_is_deleted(connecting):
    window = connecting(ConnectionType.REGULAR)
    click(window, view_pos(window, 0, 0))

    window.node_delete_coordinator.delete_nodes({1})

    assert window.node_connect_coordinator.start_node is None


def test_loading_data_ends_chain(connecting, write_xml):
    window = connecting(ConnectionType.REGULAR)
    click(window, view_pos(window, 0, 0))

    window.project_coordinator.load_xml_file(write_xml())

    assert window.node_connect_coordinator.start_node is None
    hover(window, QPoint(100, 100))   # must not touch the deleted preview item


@pytest.mark.parametrize("connection_type", list(ConnectionType))
def test_chaining_keeps_previous_connection_drawn(connecting, connection_type):
    # Reported bug: reverse A -> B disappeared after connecting B -> C,
    # because B does not list A for a reverse connection.
    window = connecting(connection_type)
    click(window, view_pos(window, 0, 0))
    click(window, view_pos(window, 20, 0))   # 1 -> 3
    click(window, view_pos(window, 10, 0))   # 3 -> 2

    assert state(window, 1, 3) == CONNECTION_STATES[connection_type]
    assert [c.connection_type for c in connections_between(window, 1, 3)] == [connection_type]
