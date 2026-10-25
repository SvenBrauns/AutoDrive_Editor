"""Creating nodes: the command and the "Erstellen" tool."""

import pytest
from mouse_helpers import click, cursor_shape, drag, hover, view_pos
from PySide6.QtCore import QPoint, Qt

from autodrive_editor.editing.commands.create_node import CreateNodeCommand
from autodrive_editor.editing.operations.create_nodes import CreateNodesOperation
from autodrive_editor.model.autodrive_data import AutoDriveData, NodeData
from autodrive_editor.ui.tools.interaction_mode import InteractionMode

# Test network from conftest: nodes 1, 2, 3 on z=0 at x = 0, 10, 20, y = 0.

EMPTY = (5, 20)


# --- command ------------------------------------------------------------


def test_command_adds_and_removes_node():
    data = AutoDriveData()
    command = CreateNodeCommand(data, 7, 1.5, 2.5, 3.5)

    command.redo()
    node = data.get_node(7)
    assert (node.x, node.y, node.z, node.flag) == (1.5, 2.5, 3.5, 0)
    assert node.incoming == node.outgoing == set()

    command.undo()
    assert 7 not in data.nodes


def test_command_reports_added_and_removed_node():
    data = AutoDriveData()
    changes = []
    command = CreateNodeCommand(data, 1, 0, 0, 0)
    command.set_change_listener(changes.append)

    command.redo()
    command.undo()

    assert changes[0].added_node_ids == {1}
    assert changes[1].removed_node_ids == {1}


def test_command_rejects_existing_id():
    data = AutoDriveData()
    data.add_node(NodeData(1, 0, 0, 0))

    with pytest.raises(ValueError):
        CreateNodeCommand(data, 1, 0, 0, 0)


def test_next_id_follows_the_highest_id_even_with_gaps():
    data = AutoDriveData()
    for node_id in (1, 2, 5):
        data.add_node(NodeData(node_id, 0, 0, 0))

    assert CreateNodesOperation.next_node_id(data) == 6
    assert CreateNodesOperation.next_node_id(AutoDriveData()) == 1


# --- tool ---------------------------------------------------------------


@pytest.fixture
def creating(zoomed_window):
    zoomed_window.set_interaction_mode(InteractionMode.CREATE_NODES)
    return zoomed_window


def data(window):
    return window.project_coordinator.autodrive_data


def visible_items(window):
    return set(window.scene_renderer.visible_node_manager.visible_node_items)


def test_click_on_empty_map_creates_a_node_there(creating):
    click(creating, view_pos(creating, *EMPTY))

    node = data(creating).get_node(4)
    assert (node.x, node.z) == pytest.approx(EMPTY, abs=0.3)
    assert node.flag == 0
    assert node.incoming == node.outgoing == set()
    assert 4 in visible_items(creating)
    assert creating.status.text() == "Node 4 erstellt"
    assert creating.actions.undo_action.text() == "Rückgängig: Node erstellen"


def test_each_click_creates_the_next_id(creating):
    click(creating, view_pos(creating, 5, 20))
    click(creating, view_pos(creating, 15, 20))

    assert sorted(data(creating).nodes) == [1, 2, 3, 4, 5]
    assert creating.edit_history.undo_stack.count() == 2


def test_click_on_existing_node_creates_nothing(creating):
    click(creating, view_pos(creating, 10, 0))

    assert len(data(creating)) == 3
    assert creating.edit_history.undo_stack.count() == 0


def test_dragging_pans_without_creating(creating):
    start = view_pos(creating, *EMPTY)

    drag(creating, start, start + QPoint(60, 0))

    assert len(data(creating)) == 3


def test_undo_removes_node_and_its_item(creating):
    click(creating, view_pos(creating, *EMPTY))

    creating.actions.undo_action.trigger()

    assert 4 not in data(creating).nodes
    assert 4 not in visible_items(creating)


def test_new_node_can_be_connected(creating):
    click(creating, view_pos(creating, *EMPTY))
    creating.set_interaction_mode(InteractionMode.CONNECT_REGULAR)

    click(creating, view_pos(creating, 0, 0))
    click(creating, view_pos(creating, *EMPTY))

    assert data(creating).get_node(1).outgoing == {2, 4}


def test_height_comes_from_the_heightmap(creating, sloped_heightmap):
    creating.heightmap.load(sloped_heightmap)

    click(creating, view_pos(creating, *EMPTY))

    node = data(creating).get_node(4)
    assert node.y == pytest.approx(creating._get_terrain_height(node.x, node.z))
    assert node.y != 0


def test_without_heightmap_height_of_nearest_node_is_used(creating):
    data(creating).get_node(3).y = 42.0  # nearest to (22, 3)

    click(creating, view_pos(creating, 22, 3))

    assert data(creating).get_node(4).y == 42.0


def test_cursor_is_cross_on_empty_map(creating):
    hover(creating, view_pos(creating, *EMPTY))
    assert cursor_shape(creating) == Qt.CrossCursor

    hover(creating, view_pos(creating, 10, 0))
    assert cursor_shape(creating) == Qt.ArrowCursor


def test_without_loaded_data_nothing_is_created(window):
    window.set_interaction_mode(InteractionMode.CREATE_NODES)

    click(window, QPoint(300, 300))

    assert window.project_coordinator.autodrive_data is None
    assert window.status.text() == "Zuerst eine AutoDrive-XML laden"


# --- subprio ------------------------------------------------------------


def test_subprio_tool_creates_subprio_node(zoomed_window):
    zoomed_window.set_interaction_mode(InteractionMode.CREATE_SUBPRIO_NODES)

    click(zoomed_window, view_pos(zoomed_window, *EMPTY))

    node = data(zoomed_window).get_node(4)
    assert node.flag == 1
    assert node.is_subprio
    assert zoomed_window.status.text() == "Subprio-Node 4 erstellt"
    assert zoomed_window.actions.undo_action.text() == "Rückgängig: Subprio-Node erstellen"


def test_subprio_node_is_drawn_orange(zoomed_window):
    zoomed_window.set_interaction_mode(InteractionMode.CREATE_SUBPRIO_NODES)

    click(zoomed_window, view_pos(zoomed_window, *EMPTY))

    item = zoomed_window.scene_renderer.visible_node_manager.visible_node_items[4]
    assert item.brush().color().name() == "#ffa500"


def test_regular_tool_still_creates_regular_nodes(creating):
    click(creating, view_pos(creating, *EMPTY))

    assert data(creating).get_node(4).flag == 0
    item = creating.scene_renderer.visible_node_manager.visible_node_items[4]
    assert item.brush().color().name() == "#ff0000"
