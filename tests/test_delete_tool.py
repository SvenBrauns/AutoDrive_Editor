"""The "Löschen" tool and the Del shortcut, driven by real input."""

import pytest

from PySide6.QtCore import QPoint, QRectF, Qt
from PySide6.QtGui import QPainterPath
from PySide6.QtTest import QTest

from mouse_helpers import click, cursor_shape, drag, hover, view_pos
from ui.interaction_mode import InteractionMode

# Test network from conftest: 1 -> 2 -> 3 on the line z=0 at x = 0, 10, 20.


@pytest.fixture
def deleting(zoomed_window):
    zoomed_window.set_interaction_mode(InteractionMode.DELETE_NODES)
    return zoomed_window


def data(window):
    return window.project_coordinator.autodrive_data


def visible_items(window):
    return set(window.scene_renderer.visible_node_manager.visible_node_items)


def select_area(window, rect):
    path = QPainterPath()
    path.addRect(rect)
    window.selection_coordinator.handle_area(path, Qt.NoModifier)


def test_click_on_node_deletes_it(deleting):
    click(deleting, view_pos(deleting, 10, 0))

    assert sorted(data(deleting).nodes) == [1, 3]
    assert data(deleting).get_node(1).outgoing == set()
    assert visible_items(deleting) == {1, 3}
    assert deleting.status.text() == "Node gelöscht"
    assert deleting.actions.undo_action.text() == "Rückgängig: Node löschen"


def test_click_on_selected_node_deletes_whole_selection(deleting):
    select_area(deleting, QRectF(-5, -5, 20, 10))   # nodes 1 and 2

    click(deleting, view_pos(deleting, 0, 0))

    assert sorted(data(deleting).nodes) == [3]
    assert deleting.node_selection_manager.selected_node_ids == set()
    assert deleting.status.text() == "2 Nodes gelöscht"


def test_click_on_unselected_node_keeps_selection(deleting):
    select_area(deleting, QRectF(-5, -5, 10, 10))   # node 1

    click(deleting, view_pos(deleting, 20, 0))

    assert sorted(data(deleting).nodes) == [1, 2]
    assert deleting.node_selection_manager.selected_node_ids == {1}


def test_click_on_empty_map_deletes_nothing(deleting):
    click(deleting, view_pos(deleting, 5, 20))

    assert len(data(deleting)) == 3
    assert deleting.edit_coordinator.undo_stack.count() == 0


def test_dragging_from_a_node_pans_instead_of_deleting(deleting):
    start = view_pos(deleting, 10, 0)

    drag(deleting, start, start + QPoint(60, 0))

    assert len(data(deleting)) == 3


def test_undo_brings_node_items_and_connections_back(deleting):
    click(deleting, view_pos(deleting, 10, 0))

    deleting.actions.undo_action.trigger()

    assert sorted(data(deleting).nodes) == [1, 2, 3]
    assert data(deleting).get_node(1).outgoing == {2}
    assert visible_items(deleting) == {1, 2, 3}
    connections = deleting.scene_renderer.connection_spatial_index.get_connections_in_rect(
        QRectF(-100, -100, 200, 200)
    )
    assert len(connections) == 2


def test_cursor_points_at_nodes(deleting):
    hover(deleting, view_pos(deleting, 10, 0))
    assert cursor_shape(deleting) == Qt.PointingHandCursor

    hover(deleting, view_pos(deleting, 5, 20))
    assert cursor_shape(deleting) == Qt.OpenHandCursor


def test_panel_has_delete_tool(window):
    texts = [action.text() for action in window.actions.tool_panel.tool_buttons]

    assert "Löschen" in texts


# --- Bearbeiten > Auswahl löschen (Entf) --------------------------------

def press_delete_key(window, qapp):
    window.activateWindow()
    window.view.setFocus()
    qapp.processEvents()
    QTest.keyClick(window.view, Qt.Key_Delete)
    qapp.processEvents()


def test_delete_selection_action_follows_selection(zoomed_window):
    action = zoomed_window.actions.delete_selection_action
    assert not action.isEnabled()

    select_area(zoomed_window, QRectF(-5, -5, 10, 10))
    assert action.isEnabled()

    zoomed_window.selection_coordinator.clear()
    assert not action.isEnabled()


def test_delete_key_deletes_selection_in_any_tool(zoomed_window, qapp):
    zoomed_window.set_interaction_mode(InteractionMode.SELECT)
    select_area(zoomed_window, QRectF(5, -5, 20, 10))   # nodes 2 and 3

    press_delete_key(zoomed_window, qapp)

    assert sorted(data(zoomed_window).nodes) == [1]
    assert not zoomed_window.actions.delete_selection_action.isEnabled()


def test_delete_is_blocked_during_a_node_drag(zoomed_window, qapp):
    zoomed_window.set_interaction_mode(InteractionMode.MOVE_NODES)
    select_area(zoomed_window, QRectF(15, -5, 10, 10))   # node 3
    start = view_pos(zoomed_window, 0, 0)
    drag(zoomed_window, start, start + QPoint(40, 0), release=False)

    press_delete_key(zoomed_window, qapp)

    assert sorted(data(zoomed_window).nodes) == [1, 2, 3]
