import pytest

from autodrive.models import AutoDriveData, NodeData
from editing.move_nodes_command import MoveNodesCommand


@pytest.fixture
def data():
    autodrive_data = AutoDriveData()
    autodrive_data.add_node(NodeData(node_id=1, x=0, y=5, z=0))
    autodrive_data.add_node(NodeData(node_id=2, x=10, y=5, z=0))
    return autodrive_data


def position(data, node_id):
    node = data.get_node(node_id)
    return (node.x, node.y, node.z)


def test_redo_moves_and_undo_restores(data):
    command = MoveNodesCommand(data, {1: (0, 5, 0)}, {1: (3, 6, 4)})

    command.redo()
    assert position(data, 1) == (3, 6, 4)

    command.undo()
    assert position(data, 1) == (0, 5, 0)


def test_moves_several_nodes_together(data):
    command = MoveNodesCommand(
        data,
        {1: (0, 5, 0), 2: (10, 5, 0)},
        {1: (1, 5, 1), 2: (11, 5, 1)}
    )

    command.redo()

    assert position(data, 1) == (1, 5, 1)
    assert position(data, 2) == (11, 5, 1)
    assert command.text() == "2 Nodes verschieben"


def test_reports_changed_node_ids(data):
    changes = []
    command = MoveNodesCommand(data, {2: (10, 5, 0)}, {2: (20, 5, 0)})
    command.set_change_listener(changes.append)

    command.redo()
    command.undo()

    assert [change.changed_node_ids for change in changes] == [{2}, {2}]


def test_rejects_unknown_node(data):
    with pytest.raises(ValueError):
        MoveNodesCommand(data, {99: (0, 0, 0)}, {99: (1, 1, 1)})


def test_rejects_mismatched_node_sets(data):
    with pytest.raises(ValueError):
        MoveNodesCommand(data, {1: (0, 5, 0)}, {2: (1, 5, 1)})


def test_rejects_empty_move(data):
    with pytest.raises(ValueError):
        MoveNodesCommand(data, {}, {})


def test_move_to_same_position_is_obsolete(data):
    command = MoveNodesCommand(data, {1: (0, 5, 0)}, {1: (0, 5, 0)})

    assert command.isObsolete()


def test_commands_without_merge_key_do_not_merge(data):
    first = MoveNodesCommand(data, {1: (0, 5, 0)}, {1: (1, 5, 0)})
    second = MoveNodesCommand(data, {1: (1, 5, 0)}, {1: (2, 5, 0)})

    assert first.id() == -1
    assert not first.mergeWith(second)


def test_same_merge_key_merges_into_one_move(data):
    first = MoveNodesCommand(data, {1: (0, 5, 0)}, {1: (1, 5, 0)}, merge_key="drag-1")
    second = MoveNodesCommand(data, {1: (1, 5, 0)}, {1: (2, 5, 0)}, merge_key="drag-1")

    assert first.mergeWith(second)
    assert first.old_positions == {1: (0.0, 5.0, 0.0)}
    assert first.new_positions == {1: (2.0, 5.0, 0.0)}


def test_different_merge_keys_do_not_merge(data):
    first = MoveNodesCommand(data, {1: (0, 5, 0)}, {1: (1, 5, 0)}, merge_key="drag-1")
    second = MoveNodesCommand(data, {1: (1, 5, 0)}, {1: (2, 5, 0)}, merge_key="drag-2")

    assert not first.mergeWith(second)


def test_merge_back_to_start_becomes_obsolete(data):
    first = MoveNodesCommand(data, {1: (0, 5, 0)}, {1: (1, 5, 0)}, merge_key="drag")
    back = MoveNodesCommand(data, {1: (1, 5, 0)}, {1: (0, 5, 0)}, merge_key="drag")

    first.mergeWith(back)

    assert first.isObsolete()
