"""Find route tool with the real window."""

import time

import pytest
from costmap_helpers import make_costmap
from mouse_helpers import click, drag, hover, press_escape, view_pos
from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from autodrive_editor.ui.tools.find_route_tool import HOVER_COLOR
from autodrive_editor.ui.tools.generate_tool import GenerateTask
from autodrive_editor.ui.tools.interaction_mode import InteractionMode

# Test network from conftest: nodes 1, 2, 3 on z=0 at x = 0, 10, 20.


@pytest.fixture
def window(zoomed_window):
    zoomed_window.find_route_operation.costmap_provider = make_costmap
    zoomed_window.set_generate_task(GenerateTask.ROUTE)

    return zoomed_window


def wait(window):
    deadline = time.monotonic() + 30

    while window.find_route_operation.is_searching and time.monotonic() < deadline:
        QApplication.processEvents()
        time.sleep(0.01)


def waypoint_ids(window):
    return [waypoint.node_id for waypoint in window.find_route_operation.waypoints]


def test_clicks_on_free_ground_and_nodes_add_waypoints_and_show_the_route(window):
    click(window, view_pos(window, 0, 20))
    click(window, view_pos(window, 20, 0))
    wait(window)

    assert waypoint_ids(window) == [None, 3]
    tool = window.generate_tool.current
    assert tool._route_item.isVisible() and not tool._route_item.path().isEmpty()
    assert tool._blocked_item.path().isEmpty()
    assert tool._gap_item.path().isEmpty()


def test_a_gap_is_drawn_where_no_route_was_found(window, monkeypatch):
    # No built leg, and the search gets stuck at once.
    monkeypatch.setattr("autodrive_editor.editing.route_pipeline.LegBuilder.build", lambda *a: None)
    monkeypatch.setattr("autodrive_editor.editing.route_finder.MAX_EXPANSIONS", 1)
    monkeypatch.setattr(
        "autodrive_editor.editing.route_finder._Search._dubins_end", lambda *a: None
    )
    click(window, view_pos(window, 0, 20))
    click(window, view_pos(window, 40, 20))
    wait(window)

    tool = window.generate_tool.current
    assert tool._gap_item.isVisible() and not tool._gap_item.path().isEmpty()


def test_dragging_a_node_moves_it_and_adds_no_waypoint(window):
    drag(window, view_pos(window, 10, 0), view_pos(window, 10, 0) + QPoint(0, 40))

    assert window.project_coordinator.autodrive_data.nodes[2].z > 2
    assert waypoint_ids(window) == []


def test_dragging_a_free_waypoint_moves_it(window):
    click(window, view_pos(window, 0, 20))
    start = view_pos(window, 0, 20)
    drag(window, start, start + QPoint(40, 0))

    assert window.find_route_operation.waypoints[0].x > 2


def test_right_click_backspace_and_escape_remove_waypoints(window):
    for x in (0, 10, 20):
        click(window, view_pos(window, x, 20))

    click(window, view_pos(window, 10, 20), Qt.RightButton)
    assert len(window.find_route_operation.waypoints) == 2

    QTest.keyClick(window.view, Qt.Key_Backspace)
    assert len(window.find_route_operation.waypoints) == 1

    press_escape(window)
    assert window.find_route_operation.waypoints == []


def test_without_drivability_map_no_waypoint_is_added(window):
    window.find_route_operation.costmap_provider = lambda: None

    click(window, view_pos(window, 0, 20))

    assert waypoint_ids(window) == []
    assert "drivability map" in window.status.text()


def test_selecting_generate_starts_planning_mode(window):
    assert window.edit_history.is_planning
    assert window.actions.generate_action.shortcut().toString() == "G"


def test_confirm_after_applied_plan_adds_the_route_to_a_new_plan(window):
    window.planning.apply_button.click()
    click(window, view_pos(window, 0, 20))
    window.planning.apply_button.click()
    click(window, view_pos(window, 20, 0))
    window.planning.apply_button.click()
    wait(window)

    assert window.generate_tool.confirm()
    assert window.edit_history.is_planning and window.edit_history.has_plan_edits


def test_discarding_the_plan_removes_routes_and_waypoints(window):
    data = window.project_coordinator.autodrive_data
    click(window, view_pos(window, 0, 20))
    click(window, view_pos(window, 20, 0))
    wait(window)
    window.generate_tool.confirm()
    click(window, view_pos(window, 0, -20))

    window.planning.discard_button.click()
    wait(window)

    assert list(data.nodes) == [1, 2, 3]
    assert waypoint_ids(window) == []
    assert window.find_route_operation.shown_route is None


def test_the_options_pick_what_generate_creates(window):
    window.set_interaction_mode(InteractionMode.SELECT)

    window.actions.generate_task_actions[GenerateTask.PARKING_SPOTS].trigger()

    assert window.generate_tool.task == GenerateTask.PARKING_SPOTS
    assert window.view.active_tool is window.generate_tool


def test_menu_entry_and_button_pick_the_same_task(window):
    window.set_interaction_mode(InteractionMode.SELECT)
    menu = next(a.menu() for a in window.menuBar().actions() if a.text() == "Generate")
    entries = [a for a in menu.actions() if not a.isSeparator()]
    buttons = window.generate_options.task_buttons

    assert [a.text() for a in entries] == [
        "Route",
        "Junction",
        "Parking spots",
        "Stations",
        "Building types…",
    ]

    entries[3].trigger()

    assert window.generate_tool.task == GenerateTask.STATIONS
    assert window.view.interaction_mode == InteractionMode.GENERATE
    assert buttons[GenerateTask.STATIONS].defaultAction() is entries[3]
    assert buttons[GenerateTask.STATIONS].isChecked()


def test_the_generate_button_shows_the_current_task(window):
    window.set_generate_task(GenerateTask.JUNCTION)
    generate = window.actions.generate_action
    junction = window.actions.generate_task_actions[GenerateTask.JUNCTION]

    assert generate.icon().cacheKey() == junction.icon().cacheKey()
    assert "<b>Generate – Junction</b> (G)" in generate.toolTip()
    assert junction.isChecked()


def test_dragging_the_route_inserts_a_waypoint_there(window):
    click(window, view_pos(window, 0, 20))
    click(window, view_pos(window, 40, 20))
    wait(window)

    drag(window, view_pos(window, 20, 20), view_pos(window, 20, 26))
    wait(window)

    waypoints = window.find_route_operation.waypoints
    assert len(waypoints) == 3
    assert waypoints[1].x == pytest.approx(20, abs=0.5)
    assert waypoints[1].z == pytest.approx(26, abs=0.5)
    route = window.find_route_operation.route
    assert route.points[route.waypoint_indices[1]] == pytest.approx(
        (waypoints[1].x, waypoints[1].z)
    )


def test_click_on_a_connection_adds_a_waypoint_on_it(window):
    click(window, view_pos(window, 5, 0))

    waypoint = window.find_route_operation.waypoints[0]
    assert waypoint.connection in {(1, 2), (2, 1)}
    assert (waypoint.x, waypoint.z) == pytest.approx((5, 0), abs=0.5)


def test_delete_removes_the_waypoint_under_the_pointer_not_the_selection(window):
    window.node_selection.replace({1}, 1)
    for x in (0, 10, 20):
        click(window, view_pos(window, x, 20))
    tool = window.generate_tool.current

    hover(window, view_pos(window, 10, 20))
    assert tool._handle_items[1].pen().color() == HOVER_COLOR

    QTest.keyClick(window.view, Qt.Key_Delete)

    assert [round(w.x) for w in window.find_route_operation.waypoints] == [0, 20]
    assert 1 in window.project_coordinator.autodrive_data.nodes

    window.delete_selection()  # the Delete action: nothing hovered, deletes the selection
    assert 1 not in window.project_coordinator.autodrive_data.nodes


def test_ctrl_z_first_takes_back_waypoints_then_the_plan(window):
    click(window, view_pos(window, 0, 20))
    click(window, view_pos(window, 20, 20))
    assert window.actions.undo_action.isEnabled()

    window.actions.undo_action.trigger()

    assert len(window.find_route_operation.waypoints) == 1


def test_enter_starts_empty(window):
    click(window, view_pos(window, 0, 20))
    click(window, view_pos(window, 20, 0))
    wait(window)

    assert window.generate_tool.confirm()

    assert window.find_route_operation.waypoints == []


def test_options_bar_buttons_remove_the_last_waypoint_and_clear(window):
    for x in (0, 10, 20):
        click(window, view_pos(window, x, 20))
    options = window.generate_options
    assert options.route_options.isEnabled()

    options.remove_last_button.click()
    assert len(window.find_route_operation.waypoints) == 2

    options.clear_button.click()
    assert window.find_route_operation.waypoints == []
