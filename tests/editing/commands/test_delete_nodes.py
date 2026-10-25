import copy

import pytest

from autodrive_editor.editing.commands.delete_nodes import DeleteNodesCommand
from autodrive_editor.model.autodrive_data import AutoDriveData, MarkerData, NodeData


@pytest.fixture
def data():
    """1 -> 2 regular, 2 <-> 3 dual, 4 -> 2 reverse (2 does not list 4
    as incoming), marker on node 2."""

    autodrive_data = AutoDriveData()
    autodrive_data.add_node(NodeData(1, 0, 0, 0, outgoing={2}))
    autodrive_data.add_node(NodeData(2, 10, 0, 0, incoming={1, 3}, outgoing={3}))
    autodrive_data.add_node(NodeData(3, 20, 0, 0, incoming={2}, outgoing={2}))
    autodrive_data.add_node(NodeData(4, 10, 0, 10, outgoing={2}))
    autodrive_data.add_marker(MarkerData(node_id=2, name="Hof", group="All"))
    return autodrive_data


def snapshot(data):
    return copy.deepcopy((data.nodes, data.markers))


def test_delete_removes_node_marker_and_all_references(data):
    DeleteNodesCommand(data, {2}).redo()

    assert 2 not in data.nodes
    assert 2 not in data.markers
    assert data.get_node(1).outgoing == set()
    assert data.get_node(3).incoming == set()
    assert data.get_node(3).outgoing == set()
    assert data.get_node(4).outgoing == set()  # reverse connection found too
    assert data.validate_connections() == []


def test_undo_restores_everything_exactly(data):
    before = snapshot(data)
    command = DeleteNodesCommand(data, {2})

    command.redo()
    command.undo()

    assert snapshot(data) == before


def test_redo_after_undo_deletes_again(data):
    command = DeleteNodesCommand(data, {2})

    command.redo()
    command.undo()
    command.redo()

    assert 2 not in data.nodes
    assert data.get_node(4).outgoing == set()


def test_deleting_connected_nodes_together(data):
    before = snapshot(data)
    command = DeleteNodesCommand(data, {2, 3})

    command.redo()
    assert sorted(data.nodes) == [1, 4]
    assert data.validate_connections() == []

    command.undo()
    assert snapshot(data) == before


def test_ids_are_not_renumbered(data):
    DeleteNodesCommand(data, {2}).redo()

    assert sorted(data.nodes) == [1, 3, 4]


def test_reports_removed_and_neighbor_nodes(data):
    changes = []
    command = DeleteNodesCommand(data, {2})
    command.set_change_listener(changes.append)

    command.redo()
    command.undo()

    removed, added = changes
    assert removed.removed_node_ids == {2}
    assert removed.connection_node_ids == {1, 3, 4}
    assert added.added_node_ids == {2}
    assert added.connection_node_ids == {1, 3, 4}


def test_command_text():
    data = AutoDriveData()
    data.add_node(NodeData(1, 0, 0, 0))
    data.add_node(NodeData(2, 0, 0, 0))

    assert DeleteNodesCommand(data, {1}).text() == "Node löschen"
    assert DeleteNodesCommand(data, {1, 2}).text() == "2 Nodes löschen"


def test_rejects_unknown_or_empty(data):
    with pytest.raises(ValueError):
        DeleteNodesCommand(data, {99})

    with pytest.raises(ValueError):
        DeleteNodesCommand(data, set())


def test_undo_puts_markers_back_in_their_order():
    data = AutoDriveData()
    for node_id in (1, 2, 3):
        data.add_node(NodeData(node_id, 0, 0, 0))
    for node_id, name in ((3, "first"), (1, "second"), (2, "third")):
        data.add_marker(MarkerData(node_id=node_id, name=name))
    command = DeleteNodesCommand(data, {1})

    command.redo()
    assert [m.name for m in data.markers.values()] == ["first", "third"]

    command.undo()
    assert [m.name for m in data.markers.values()] == ["first", "second", "third"]
