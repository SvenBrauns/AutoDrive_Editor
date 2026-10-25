"""Each map tool driven by real mouse and key events."""

import pytest
from mouse_helpers import click, cursor_shape, drag, hover, press_escape, send_mouse, view_pos
from PySide6.QtCore import QEvent, QPoint, Qt

from autodrive_editor.measurement.mode import MeasurementMode
from autodrive_editor.ui.tools.interaction_mode import InteractionMode
from autodrive_editor.ui.tools.map_tool import MapTool

EMPTY = (5, 20)  # map position between the nodes, below the line


def selected(window):
    return window.node_selection.selected_node_ids


def scroll_position(window):
    return (window.view.horizontalScrollBar().value(), window.view.verticalScrollBar().value())


@pytest.fixture
def select_mode(zoomed_window):
    zoomed_window.set_interaction_mode(InteractionMode.SELECT)
    return zoomed_window


# --- MapView -----------------------------------------------------------


def test_each_mode_has_its_own_tool(window):
    tools = {mode: window.view._tools[mode] for mode in InteractionMode}

    assert all(isinstance(tool, MapTool) for tool in tools.values())
    assert len({id(tool) for tool in tools.values()}) == len(InteractionMode)


def test_switching_mode_switches_active_tool(window):
    window.set_interaction_mode(InteractionMode.MOVE_NODES)
    assert window.view.active_tool is window.view._tools[InteractionMode.MOVE_NODES]

    window.set_measurement_mode(MeasurementMode.DISTANCE)
    assert window.view.active_tool is window.view._measure_tool

    window.set_measurement_mode(MeasurementMode.INACTIVE)
    assert window.view.active_tool is window.view._tools[InteractionMode.MOVE_NODES]


@pytest.mark.parametrize("mode", list(InteractionMode))
def test_middle_drag_rotates_in_every_tool(zoomed_window, mode):
    zoomed_window.set_interaction_mode(mode)
    start = QPoint(400, 300)

    drag(zoomed_window, start, start + QPoint(80, 0), button=Qt.MiddleButton, release=False)
    assert cursor_shape(zoomed_window) == Qt.SizeAllCursor
    send_mouse(
        zoomed_window,
        QEvent.MouseButtonRelease,
        start + QPoint(80, 0),
        Qt.MiddleButton,
        Qt.NoButton,
    )

    assert zoomed_window.view.rotation_angle != 0


@pytest.mark.parametrize("mode", list(InteractionMode))
def test_left_drag_on_empty_map_pans_in_every_tool(zoomed_window, mode):
    # The three test nodes fit on screen, so give the map room to pan.
    zoomed_window.view.setSceneRect(-1000, -1000, 2000, 2000)
    zoomed_window.set_interaction_mode(mode)
    before = scroll_position(zoomed_window)
    start = view_pos(zoomed_window, *EMPTY)

    drag(zoomed_window, start, start + QPoint(60, 30))

    assert scroll_position(zoomed_window) != before
    assert zoomed_window.edit_history.undo_stack.count() == 0


# --- Navigation --------------------------------------------------------


def test_navigation_click_does_not_select(zoomed_window):
    click(zoomed_window, view_pos(zoomed_window, 10, 0))

    assert selected(zoomed_window) == set()
    assert cursor_shape(zoomed_window) == Qt.OpenHandCursor


# --- Auswahl -----------------------------------------------------------


def test_click_selects_and_ctrl_click_toggles(select_mode):
    click(select_mode, view_pos(select_mode, 0, 0))
    assert selected(select_mode) == {1}

    click(select_mode, view_pos(select_mode, 20, 0), modifiers=Qt.ControlModifier)
    assert selected(select_mode) == {1, 3}

    click(select_mode, view_pos(select_mode, 0, 0), modifiers=Qt.ControlModifier)
    assert selected(select_mode) == {3}


def test_click_on_empty_map_clears_selection(select_mode):
    click(select_mode, view_pos(select_mode, 0, 0))

    click(select_mode, view_pos(select_mode, *EMPTY))

    assert selected(select_mode) == set()


def test_left_drag_does_not_change_selection(select_mode):
    click(select_mode, view_pos(select_mode, 0, 0))
    start = view_pos(select_mode, 10, 0)

    drag(select_mode, start, start + QPoint(60, 0))

    assert selected(select_mode) == {1}


def test_right_drag_box_selects(select_mode):
    drag(
        select_mode,
        view_pos(select_mode, -5, -5),
        view_pos(select_mode, 15, 5),
        button=Qt.RightButton,
    )

    assert selected(select_mode) == {1, 2}


def test_escape_cancels_box_selection(select_mode):
    drag(
        select_mode,
        view_pos(select_mode, -5, -5),
        view_pos(select_mode, 25, 5),
        button=Qt.RightButton,
        release=False,
    )
    assert cursor_shape(select_mode) == Qt.CrossCursor

    press_escape(select_mode)
    send_mouse(
        select_mode,
        QEvent.MouseButtonRelease,
        view_pos(select_mode, 25, 5),
        Qt.RightButton,
        Qt.NoButton,
    )

    assert selected(select_mode) == set()


def test_switching_tool_cancels_box_selection(select_mode):
    drag(
        select_mode,
        view_pos(select_mode, -5, -5),
        view_pos(select_mode, 25, 5),
        button=Qt.RightButton,
        release=False,
    )

    select_mode.set_interaction_mode(InteractionMode.NAVIGATE)
    send_mouse(
        select_mode,
        QEvent.MouseButtonRelease,
        view_pos(select_mode, 25, 5),
        Qt.RightButton,
        Qt.NoButton,
    )

    assert selected(select_mode) == set()


def test_select_cursor_is_arrow_over_node(select_mode):
    hover(select_mode, view_pos(select_mode, 10, 0))
    assert cursor_shape(select_mode) == Qt.ArrowCursor

    hover(select_mode, view_pos(select_mode, *EMPTY))
    assert cursor_shape(select_mode) == Qt.OpenHandCursor


# --- Verschieben -------------------------------------------------------


def test_move_cursor_is_move_arrow_over_node(zoomed_window):
    zoomed_window.set_interaction_mode(InteractionMode.MOVE_NODES)

    hover(zoomed_window, view_pos(zoomed_window, 10, 0))

    assert cursor_shape(zoomed_window) == Qt.SizeAllCursor


# --- Messen ------------------------------------------------------------


@pytest.fixture
def measuring(zoomed_window):
    zoomed_window.set_measurement_mode(MeasurementMode.DISTANCE)
    return zoomed_window


def test_two_clicks_complete_a_measurement(measuring):
    click(measuring, view_pos(measuring, *EMPTY))
    click(measuring, view_pos(measuring, 15, 25))

    assert measuring.measurement_controller.is_complete
    assert cursor_shape(measuring) == Qt.CrossCursor


def test_hover_shows_preview_to_second_point(measuring):
    click(measuring, view_pos(measuring, *EMPTY))

    hover(measuring, view_pos(measuring, 15, 25))

    assert measuring.measurement_controller.state.preview_position is not None


def test_dragging_empty_map_pans_without_setting_a_point(measuring):
    start = view_pos(measuring, *EMPTY)

    drag(measuring, start, start + QPoint(60, 0))

    assert not measuring.measurement_controller.state.has_start_point


def test_dragging_a_free_point_moves_it(measuring):
    click(measuring, view_pos(measuring, *EMPTY))
    click(measuring, view_pos(measuring, 15, 25))
    start = view_pos(measuring, 15, 25)

    drag(measuring, start, start + QPoint(40, 0), release=False)
    assert cursor_shape(measuring) == Qt.SizeAllCursor
    send_mouse(
        measuring, QEvent.MouseButtonRelease, start + QPoint(40, 0), Qt.LeftButton, Qt.NoButton
    )

    end_point = measuring.measurement_controller.state.end_point
    assert end_point.x == pytest.approx(25, abs=0.5)
    assert measuring.status.text() == "Messpunkt verschoben"


def test_escape_clears_measurement_then_ends_measuring(measuring):
    click(measuring, view_pos(measuring, *EMPTY))

    press_escape(measuring)
    assert not measuring.measurement_controller.state.has_start_point
    assert measuring.view.measurement_active

    press_escape(measuring)
    assert not measuring.view.measurement_active
