import pytest

from autodrive.models import AutoDriveData, NodeData
from editing.edit_coordinator import EditCoordinator
from editing.move_nodes_command import MoveNodesCommand


@pytest.fixture
def data():
    autodrive_data = AutoDriveData()
    autodrive_data.add_node(NodeData(node_id=1, x=0, y=0, z=0))
    return autodrive_data


@pytest.fixture
def coordinator():
    return EditCoordinator()


def move(data, start_x, end_x, merge_key=None):
    return MoveNodesCommand(data, {1: (start_x, 0, 0)}, {1: (end_x, 0, 0)}, merge_key)


def node_x(data):
    return data.get_node(1).x


def test_push_applies_command(coordinator, data):
    coordinator.push(move(data, 0, 5))

    assert node_x(data) == 5
    assert coordinator.can_undo
    assert not coordinator.can_redo


def test_undo_and_redo(coordinator, data):
    coordinator.push(move(data, 0, 5))
    coordinator.push(move(data, 5, 9))

    coordinator.undo()
    assert node_x(data) == 5

    coordinator.undo()
    assert node_x(data) == 0
    assert not coordinator.can_undo

    coordinator.redo()
    coordinator.redo()
    assert node_x(data) == 9


def test_new_edit_after_undo_discards_redo(coordinator, data):
    coordinator.push(move(data, 0, 5))
    coordinator.undo()

    coordinator.push(move(data, 0, 2))

    assert not coordinator.can_redo
    assert node_x(data) == 2


def test_data_changed_is_emitted_for_push_undo_and_redo(coordinator, data):
    changes = []
    coordinator.data_changed.connect(changes.append)

    coordinator.push(move(data, 0, 5))
    coordinator.undo()
    coordinator.redo()

    assert len(changes) == 3
    assert all(change.moved_node_ids == {1} for change in changes)


def test_merged_drag_is_one_undo_step(coordinator, data):
    coordinator.push(move(data, 0, 1, merge_key="drag"))
    coordinator.push(move(data, 1, 2, merge_key="drag"))
    coordinator.push(move(data, 2, 3, merge_key="drag"))

    assert coordinator.undo_stack.count() == 1

    coordinator.undo()
    assert node_x(data) == 0


def test_move_to_same_position_adds_no_undo_step(coordinator, data):
    coordinator.push(move(data, 0, 0))

    assert coordinator.undo_stack.count() == 0


def test_clean_state_follows_history(coordinator, data):
    states = []
    coordinator.clean_changed.connect(states.append)
    assert coordinator.is_clean

    coordinator.push(move(data, 0, 5))
    assert not coordinator.is_clean

    coordinator.mark_clean()
    assert coordinator.is_clean

    coordinator.undo()
    assert not coordinator.is_clean

    assert states == [False, True, False]


def test_clear_removes_history(coordinator, data):
    coordinator.push(move(data, 0, 5))

    coordinator.clear()

    assert not coordinator.can_undo
    assert coordinator.is_clean


def test_push_rejects_plain_qundocommand(coordinator):
    from PySide6.QtGui import QUndoCommand

    with pytest.raises(TypeError):
        coordinator.push(QUndoCommand("Fremd"))
