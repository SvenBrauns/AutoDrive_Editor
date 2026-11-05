"""Parallel lane tool with the real window."""

from mouse_helpers import click, hover, view_pos

from autodrive_editor.ui.tools.interaction_mode import InteractionMode

# Test network from conftest: nodes 1, 2, 3 on z=0 at x = 0, 10, 20.


def test_preview_follows_the_pointer_and_a_click_creates_the_lane(zoomed_window):
    window = zoomed_window
    window.node_selection.replace([1, 2, 3])
    window.set_interaction_mode(InteractionMode.DRAW_PARALLEL)
    tool = window.view.active_tool

    hover(window, view_pos(window, 10, 6))

    assert tool.preview_path is not None
    assert window.parallel_lane_options.distance_box.value() == 6.0

    click(window, view_pos(window, 10, 6))

    data = window.project_coordinator.autodrive_data
    new_nodes = [node for node_id, node in data.nodes.items() if node_id > 3]
    assert new_nodes
    assert window.actions.undo_action.text() == "Undo: Create parallel lane"
    assert window.node_selection.selected_node_ids == {1, 2, 3}
