import copy

import pytest

from autodrive_editor.editing.commands.merge_nodes import MergeNodesCommand
from autodrive_editor.model.autodrive_data import AutoDriveData, MarkerData, NodeData
from autodrive_editor.model.connections import ConnectionType, get_connection_type


@pytest.fixture
def data():
    """Nodes 2 and 3 lie on top of each other. 1 -> 2 regular, 2 -> 3
    regular, 3 <-> 4 dual, 5 -> 3 reverse (3 does not list 5), marker on 1."""

    autodrive_data = AutoDriveData()
    autodrive_data.add_node(NodeData(1, 0, 0, 0, outgoing={2}))
    autodrive_data.add_node(NodeData(2, 10, 0, 0, incoming={1}, outgoing={3}))
    autodrive_data.add_node(NodeData(3, 10, 0, 0, incoming={2, 4}, outgoing={4}))
    autodrive_data.add_node(NodeData(4, 20, 0, 0, incoming={3}, outgoing={3}))
    autodrive_data.add_node(NodeData(5, 10, 0, 10, outgoing={3}))
    autodrive_data.add_marker(MarkerData(node_id=1, name="Hof", group="All"))
    return autodrive_data


def snapshot(data):
    return copy.deepcopy((data.nodes, data.markers))


def test_kept_node_takes_over_all_connections(data):
    MergeNodesCommand(data, {2: {3}}).redo()

    nodes = data.nodes
    assert 3 not in nodes
    assert nodes[2].incoming == {1, 4}
    assert nodes[2].outgoing == {4}
    assert get_connection_type(nodes[1], nodes[2]) == ConnectionType.REGULAR
    assert get_connection_type(nodes[2], nodes[4]) == ConnectionType.DUAL
    assert get_connection_type(nodes[5], nodes[2]) == ConnectionType.REVERSE
    assert data.validate_connections() == []


def test_connections_within_the_group_are_dropped(data):
    MergeNodesCommand(data, {2: {3}}).redo()

    assert 2 not in data.nodes[2].incoming | data.nodes[2].outgoing


def test_data_change_lists_removed_and_changed_nodes(data):
    command = MergeNodesCommand(data, {2: {3}})

    change = command.apply()

    assert change.removed_node_ids == {3}
    assert change.connection_node_ids == {2, 4, 5}


def test_undo_restores_everything_exactly(data):
    before = snapshot(data)
    command = MergeNodesCommand(data, {2: {3}})

    command.redo()
    command.undo()

    assert snapshot(data) == before


def test_redo_after_undo_merges_again(data):
    command = MergeNodesCommand(data, {2: {3}})
    command.redo()
    after = snapshot(data)

    command.undo()
    command.redo()

    assert snapshot(data) == after


def test_several_groups_in_one_command(data):
    data.add_node(NodeData(6, 20, 0, 0))

    command = MergeNodesCommand(data, {2: {3}, 4: {6}})
    command.redo()

    assert set(data.nodes) == {1, 2, 4, 5}
    assert command.text() == "Merge 2 node groups"


@pytest.mark.parametrize(
    "merges",
    [{}, {2: {2}}, {2: {3}, 4: {3}}, {2: {3}, 3: {4}}, {2: {9}}, {9: {2}}, {2: {1}}],
    ids=["empty", "only kept", "twice", "kept merged", "unknown", "unknown kept", "marker"],
)
def test_invalid_merges_are_rejected(data, merges):
    with pytest.raises(ValueError):
        MergeNodesCommand(data, merges)
