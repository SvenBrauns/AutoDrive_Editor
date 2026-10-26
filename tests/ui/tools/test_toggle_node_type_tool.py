"""Switching nodes between regular and subprio."""

import pytest
from mouse_helpers import click, cursor_shape, drag, hover, view_pos
from PySide6.QtCore import QPoint, QRectF, Qt
from PySide6.QtGui import QPainterPath

from autodrive_editor.editing.commands.set_node_flags import SetNodeFlagsCommand
from autodrive_editor.model.autodrive_data import (
    REGULAR_FLAG,
    SUBPRIO_FLAG,
    AutoDriveData,
    NodeData,
)
from autodrive_editor.ui.tools.interaction_mode import InteractionMode

ORANGE = "#ffa500"
RED = "#ff0000"


# --- command ------------------------------------------------------------


@pytest.fixture
def data():
    autodrive_data = AutoDriveData()
    autodrive_data.add_node(NodeData(1, 0, 0, 0, flag=REGULAR_FLAG))
    autodrive_data.add_node(NodeData(2, 0, 0, 0, flag=SUBPRIO_FLAG))
    return autodrive_data


def test_command_sets_and_restores_flags(data):
    command = SetNodeFlagsCommand(data, {1, 2}, SUBPRIO_FLAG)

    command.redo()
    assert (data.nodes[1].flag, data.nodes[2].flag) == (1, 1)

    command.undo()
    assert (data.nodes[1].flag, data.nodes[2].flag) == (0, 1)


def test_command_text_and_change(data):
    changes = []
    command = SetNodeFlagsCommand(data, {1}, SUBPRIO_FLAG)
    command.set_change_listener(changes.append)

    command.redo()

    assert command.text() == "Set node to Subprio"
    assert SetNodeFlagsCommand(data, {1, 2}, REGULAR_FLAG).text() == "Set 2 nodes to Regular"
    assert changes[0].changed_flag_node_ids == {1}


def test_command_without_change_is_obsolete(data):
    assert SetNodeFlagsCommand(data, {2}, SUBPRIO_FLAG).isObsolete()


# --- tool ---------------------------------------------------------------
# Test network from conftest: nodes 1, 2, 3 on z=0 at x = 0, 10, 20, all regular.


@pytest.fixture
def toggling(zoomed_window):
    zoomed_window.set_interaction_mode(InteractionMode.TOGGLE_NODE_TYPE)
    return zoomed_window


def flag(window, node_id):
    return window.project_coordinator.autodrive_data.get_node(node_id).flag


def color(window, node_id):
    item = window.scene_renderer.visible_node_manager.visible_node_items[node_id]
    return item.brush().color().name()


def select(window, rect):
    path = QPainterPath()
    path.addRect(rect)
    window.selection_coordinator.handle_area(path, Qt.NoModifier)


def test_click_switches_node_and_redraws_it(toggling):
    click(toggling, view_pos(toggling, 10, 0))
    assert flag(toggling, 2) == SUBPRIO_FLAG
    assert color(toggling, 2) == ORANGE
    assert toggling.status.text() == "Node 2 set to Subprio"

    click(toggling, view_pos(toggling, 10, 0))
    assert flag(toggling, 2) == REGULAR_FLAG
    assert color(toggling, 2) == RED


def test_click_on_selected_node_switches_whole_selection(toggling):
    select(toggling, QRectF(-5, -5, 20, 10))  # nodes 1 and 2

    click(toggling, view_pos(toggling, 0, 0))

    assert (flag(toggling, 1), flag(toggling, 2), flag(toggling, 3)) == (1, 1, 0)
    assert toggling.status.text() == "2 nodes set to Subprio"
    assert toggling.actions.undo_action.text() == "Undo: Set 2 nodes to Subprio"


def test_mixed_selection_gets_opposite_of_clicked_node(toggling):
    toggling.project_coordinator.autodrive_data.get_node(1).flag = SUBPRIO_FLAG
    select(toggling, QRectF(-5, -5, 30, 10))  # 1 subprio, 2 and 3 regular

    click(toggling, view_pos(toggling, 10, 0))  # clicked node is regular

    assert (flag(toggling, 1), flag(toggling, 2), flag(toggling, 3)) == (1, 1, 1)
    assert toggling.status.text() == "2 nodes set to Subprio"


def test_selection_rings_are_redrawn_too(toggling):
    select(toggling, QRectF(-5, -5, 10, 10))  # node 1
    ring = toggling.scene_renderer.visible_node_selection_manager.visible_selection_items[1]
    assert ring.brush().color().name() == RED

    click(toggling, view_pos(toggling, 0, 0))

    ring = toggling.scene_renderer.visible_node_selection_manager.visible_selection_items[1]
    assert ring.brush().color().name() == ORANGE


def test_click_on_unselected_node_keeps_selection(toggling):
    select(toggling, QRectF(-5, -5, 10, 10))  # node 1

    click(toggling, view_pos(toggling, 20, 0))

    assert (flag(toggling, 1), flag(toggling, 3)) == (0, 1)
    assert toggling.node_selection.selected_node_ids == {1}


def test_undo_restores_type_and_color(toggling):
    click(toggling, view_pos(toggling, 10, 0))

    toggling.actions.undo_action.trigger()

    assert flag(toggling, 2) == REGULAR_FLAG
    assert color(toggling, 2) == RED


def test_node_info_shows_new_type(toggling):
    select(toggling, QRectF(5, -5, 10, 10))  # node 2
    assert "Regular node" in toggling.debug_dock.node_info_value.text()

    click(toggling, view_pos(toggling, 10, 0))

    assert "Subprio node" in toggling.debug_dock.node_info_value.text()


def test_click_on_empty_map_and_drag_change_nothing(toggling):
    click(toggling, view_pos(toggling, 5, 20))
    start = view_pos(toggling, 10, 0)
    drag(toggling, start, start + QPoint(60, 0))

    assert (flag(toggling, 1), flag(toggling, 2), flag(toggling, 3)) == (0, 0, 0)
    assert toggling.edit_history.undo_stack.count() == 0


def test_cursor_points_at_nodes(toggling):
    hover(toggling, view_pos(toggling, 10, 0))
    assert cursor_shape(toggling) == Qt.PointingHandCursor


def test_nodes_with_unknown_flag_are_not_changed(toggling):
    toggling.project_coordinator.autodrive_data.get_node(2).flag = 4

    click(toggling, view_pos(toggling, 10, 0))

    assert flag(toggling, 2) == 4
    assert toggling.edit_history.undo_stack.count() == 0
    assert "unknown type" in toggling.status.text()


def test_selection_skips_nodes_with_unknown_flag(toggling):
    toggling.project_coordinator.autodrive_data.get_node(2).flag = 4
    select(toggling, QRectF(-5, -5, 30, 10))  # all three

    click(toggling, view_pos(toggling, 0, 0))

    assert (flag(toggling, 1), flag(toggling, 2), flag(toggling, 3)) == (1, 4, 1)


def test_loaded_source_is_remembered(loaded_window):
    source = loaded_window.project_coordinator.config_source

    assert source.format.value == "route_export"


def test_map_scan_nodes_toggle_like_regular_nodes(toggling):
    toggling.project_coordinator.autodrive_data.get_node(2).flag = 2

    click(toggling, view_pos(toggling, 10, 0))
    assert flag(toggling, 2) == 1
    assert color(toggling, 2) == ORANGE

    click(toggling, view_pos(toggling, 10, 0))
    assert flag(toggling, 2) == 0


def test_undo_gives_map_scan_flag_back(toggling):
    toggling.project_coordinator.autodrive_data.get_node(2).flag = 2

    click(toggling, view_pos(toggling, 10, 0))
    toggling.actions.undo_action.trigger()

    assert flag(toggling, 2) == 2


def test_node_info_names_map_scan_and_unknown_flags(toggling):
    data = toggling.project_coordinator.autodrive_data
    data.get_node(2).flag = 2
    data.get_node(3).flag = 4
    formatter = toggling.node_info_formatter

    assert "Regular node (from map scan)" in formatter.format_node_info(data.get_node(2), data)
    assert "Regular node (flag 4)" in formatter.format_node_info(data.get_node(3), data)
