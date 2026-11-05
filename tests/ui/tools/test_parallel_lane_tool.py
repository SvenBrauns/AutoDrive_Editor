"""Parallel lane tool with the real window."""

from mouse_helpers import click, drag, hover, view_pos
from PySide6.QtCore import Qt

from autodrive_editor.ui.tools.interaction_mode import InteractionMode

# Test network from conftest: nodes 1, 2, 3 on z=0 at x = 0, 10, 20.


def test_select_with_right_drag_then_a_click_creates_the_lane(zoomed_window):
    window = zoomed_window
    window.set_interaction_mode(InteractionMode.DRAW_PARALLEL)
    tool = window.view.active_tool

    drag(window, view_pos(window, -3, -3), view_pos(window, 23, 3), button=Qt.RightButton)
    assert window.node_selection.selected_node_ids == {1, 2, 3}

    hover(window, view_pos(window, 10, 6))

    assert tool.preview_path is not None
    assert window.parallel_lane_options.distance_box.value() == 6.0

    click(window, view_pos(window, 10, 6))

    data = window.project_coordinator.autodrive_data
    assert [node_id for node_id in data.nodes if node_id > 3]
    assert window.actions.undo_action.text() == "Undo: Create parallel lane"
    assert window.node_selection.selected_node_ids == {1, 2, 3}


def test_ctrl_click_toggles_a_node_and_right_click_clears(zoomed_window):
    window = zoomed_window
    window.set_interaction_mode(InteractionMode.DRAW_PARALLEL)

    click(window, view_pos(window, 0, 0), modifiers=Qt.ControlModifier)
    assert window.node_selection.selected_node_ids == {1}

    click(window, view_pos(window, 30, 30), button=Qt.RightButton)
    assert window.node_selection.selected_node_ids == set()
    assert len(window.project_coordinator.autodrive_data.nodes) == 3
