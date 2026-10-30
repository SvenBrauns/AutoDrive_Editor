"""Find route tool with the real window."""

import time

import pytest
from costmap_helpers import make_costmap
from mouse_helpers import click, drag, press_escape, view_pos
from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from autodrive_editor.ui.tools.interaction_mode import InteractionMode

# Test network from conftest: nodes 1, 2, 3 on z=0 at x = 0, 10, 20.


@pytest.fixture
def window(zoomed_window):
    zoomed_window.find_route_operation.costmap_provider = make_costmap
    zoomed_window.set_interaction_mode(InteractionMode.FIND_ROUTE)

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
    tool = window.view.active_tool
    assert tool._route_item.isVisible() and not tool._route_item.path().isEmpty()
    assert tool._blocked_item.path().isEmpty()


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
