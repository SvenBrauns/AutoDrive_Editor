"""Node dragging driven by real mouse events on the map view."""

import pytest
from drawing_helpers import RED, drawn_color
from mouse_helpers import drag, press_escape, send_mouse, view_pos
from PySide6.QtCore import QEvent, QPoint, QRectF, Qt
from PySide6.QtGui import QPainterPath

from autodrive_editor.ui.tools.interaction_mode import InteractionMode


@pytest.fixture
def editor(zoomed_window):
    zoomed_window.set_interaction_mode(InteractionMode.MOVE_NODES)
    return zoomed_window


def node_xz(window, node_id):
    node = window.project_coordinator.autodrive_data.get_node(node_id)
    return (node.x, node.z)


def scene_delta(window, start, end):
    delta = window.view.mapToScene(end) - window.view.mapToScene(start)
    return (delta.x(), delta.y())


def select_area(window, rect):
    path = QPainterPath()
    path.addRect(rect)
    window.selection_coordinator.handle_area(path, Qt.NoModifier)


def test_dragging_unselected_node_moves_only_that_node(editor):
    select_area(editor, QRectF(5, -5, 20, 10))  # nodes 2 and 3
    start = view_pos(editor, 0, 0)
    end = start + QPoint(40, 20)
    dx, dz = scene_delta(editor, start, end)

    drag(editor, start, end)

    assert node_xz(editor, 1) == pytest.approx((dx, dz))
    assert node_xz(editor, 2) == (10, 0)
    assert editor.node_selection.selected_node_ids == {2, 3}
    assert editor.edit_history.undo_stack.count() == 1
    assert editor.status.text() == "Node moved"


def test_dragging_selected_node_moves_whole_selection(editor):
    select_area(editor, QRectF(-5, -5, 20, 10))  # nodes 1 and 2
    start = view_pos(editor, 10, 0)
    end = start + QPoint(0, 40)
    dx, dz = scene_delta(editor, start, end)

    drag(editor, start, end)

    assert node_xz(editor, 1) == pytest.approx((0 + dx, dz))
    assert node_xz(editor, 2) == pytest.approx((10 + dx, dz))
    assert node_xz(editor, 3) == (20, 0)
    assert editor.edit_history.undo_stack.count() == 1
    assert editor.edit_history.undo_stack.undoText() == "Move 2 nodes"


def test_undo_and_redo_restore_data_and_drawing(editor):
    start = view_pos(editor, 0, 0)
    drag(editor, start, start + QPoint(40, 0))
    moved = node_xz(editor, 1)

    editor.actions.undo_action.trigger()
    assert node_xz(editor, 1) == (0, 0)
    assert drawn_color(editor, 0, 0) == RED

    editor.actions.redo_action.trigger()
    assert node_xz(editor, 1) == pytest.approx(moved)
    assert drawn_color(editor, *moved) == RED
    assert drawn_color(editor, 0, 0) != RED


def test_drag_moves_connections(editor):
    start = view_pos(editor, 20, 0)
    drag(editor, start, start + QPoint(0, 40))
    x, z = node_xz(editor, 3)

    connections = editor.scene_renderer.connection_spatial_index.get_connections_in_rect(
        QRectF(-100, -100, 200, 200)
    )
    to_node_3 = [c for c in connections if 3 in (c.source_id, c.target_id)]

    assert to_node_3
    assert all((c.target_x, c.target_z) == (x, z) for c in to_node_3 if c.target_id == 3)


def test_click_does_nothing(editor):
    pos = view_pos(editor, 10, 0)

    drag(editor, pos, pos, steps=1)

    assert node_xz(editor, 2) == (10, 0)
    assert editor.node_selection.selected_node_ids == set()
    assert editor.edit_history.undo_stack.count() == 0


def test_right_drag_does_not_box_select(editor):
    start = view_pos(editor, -5, -5)
    end = view_pos(editor, 25, 5)
    send_mouse(editor, QEvent.MouseButtonPress, start, Qt.RightButton, Qt.RightButton)
    send_mouse(editor, QEvent.MouseMove, end, Qt.NoButton, Qt.RightButton)
    send_mouse(editor, QEvent.MouseButtonRelease, end, Qt.RightButton, Qt.NoButton)

    assert editor.node_selection.selected_node_ids == set()


def test_tiny_movement_below_drag_threshold_does_not_move(editor):
    pos = view_pos(editor, 10, 0)

    drag(editor, pos, pos + QPoint(1, 0), steps=1)

    assert node_xz(editor, 2) == (10, 0)


def test_escape_cancels_drag_without_undo_step(editor):
    start = view_pos(editor, 0, 0)
    drag(editor, start, start + QPoint(40, 40), release=False)
    assert node_xz(editor, 1) != (0, 0)

    press_escape(editor)
    send_mouse(editor, QEvent.MouseButtonRelease, start, Qt.LeftButton, Qt.NoButton)

    assert node_xz(editor, 1) == (0, 0)
    assert editor.edit_history.undo_stack.count() == 0
    assert not editor.isWindowModified()


def test_undo_is_blocked_while_dragging(editor):
    first = view_pos(editor, 20, 0)
    drag(editor, first, first + QPoint(0, 40))
    node_3_after_first_drag = node_xz(editor, 3)

    start = view_pos(editor, 0, 0)
    drag(editor, start, start + QPoint(40, 0), release=False)
    editor.actions.undo_action.trigger()
    send_mouse(editor, QEvent.MouseButtonRelease, start + QPoint(40, 0), Qt.LeftButton, Qt.NoButton)

    assert node_xz(editor, 3) == node_3_after_first_drag
    assert editor.edit_history.undo_stack.count() == 2


def test_dragging_empty_space_pans_instead(editor):
    start = view_pos(editor, 5, 20)  # between nodes, below the line

    drag(editor, start, start + QPoint(60, 0))

    assert node_xz(editor, 1) == (0, 0)
    assert editor.edit_history.undo_stack.count() == 0


def test_selection_mode_never_moves_nodes(editor):
    editor.set_interaction_mode(InteractionMode.SELECT)
    start = view_pos(editor, 0, 0)

    drag(editor, start, start + QPoint(40, 0))

    assert node_xz(editor, 1) == (0, 0)
    assert editor.edit_history.undo_stack.count() == 0


def test_navigation_mode_never_moves_nodes(editor):
    editor.set_interaction_mode(InteractionMode.NAVIGATE)
    start = view_pos(editor, 0, 0)

    drag(editor, start, start + QPoint(40, 0))

    assert node_xz(editor, 1) == (0, 0)


def test_switching_tool_mid_drag_cancels_it(editor):
    start = view_pos(editor, 0, 0)
    drag(editor, start, start + QPoint(40, 40), release=False)

    editor.set_interaction_mode(InteractionMode.SELECT)

    assert node_xz(editor, 1) == (0, 0)
    assert editor.edit_history.undo_stack.count() == 0
    assert not editor.edit_history.history_locked


def test_two_drags_are_two_undo_steps(editor):
    start = view_pos(editor, 0, 0)
    drag(editor, start, start + QPoint(40, 0))

    start = view_pos(editor, 20, 0)
    drag(editor, start, start + QPoint(0, 40))

    assert editor.edit_history.undo_stack.count() == 2
