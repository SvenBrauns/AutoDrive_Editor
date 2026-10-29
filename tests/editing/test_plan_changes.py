import pytest

from autodrive_editor.editing.commands.delete_nodes import DeleteNodesCommand
from autodrive_editor.editing.commands.markers import AddMarkerCommand
from autodrive_editor.editing.commands.move_nodes import MoveNodesCommand
from autodrive_editor.editing.commands.set_node_flags import SetNodeFlagsCommand
from autodrive_editor.editing.edit_history import EditHistory
from autodrive_editor.editing.plan_changes import PlanChanges
from autodrive_editor.model.autodrive_data import SUBPRIO_FLAG, AutoDriveData, NodeData


@pytest.fixture
def data():
    autodrive_data = AutoDriveData()
    autodrive_data.add_node(NodeData(1, 0, 0, 0, outgoing={2}))
    autodrive_data.add_node(NodeData(2, 10, 0, 0, incoming={1}, outgoing={3}))
    autodrive_data.add_node(NodeData(3, 20, 0, 0, incoming={2}))
    return autodrive_data


@pytest.fixture
def history(data):
    edit_history = EditHistory()
    edit_history.start_plan()
    edit_history.changes = PlanChanges(data)
    edit_history.data_changed.connect(edit_history.changes.update)
    return edit_history


def test_moved_node_is_changed(history, data):
    history.push(MoveNodesCommand(data, {1: (0, 0, 0)}, {1: (5, 0, 0)}))

    assert history.changes.changed_node_ids == {1}


def test_undone_edit_is_no_longer_changed(history, data):
    history.push(SetNodeFlagsCommand(data, {2}, SUBPRIO_FLAG))
    history.undo()

    assert history.changes.changed_node_ids == set()


def test_edit_moved_back_by_hand_is_no_longer_changed(history, data):
    history.push(MoveNodesCommand(data, {1: (0, 0, 0)}, {1: (5, 0, 0)}))
    history.push(MoveNodesCommand(data, {1: (5, 0, 0)}, {1: (0, 0, 0)}))

    assert history.changes.changed_node_ids == set()


def test_deleted_node_is_left_out_but_its_neighbours_are_changed(history, data):
    history.push(DeleteNodesCommand(data, {2}))

    assert history.changes.changed_node_ids == {1, 3}


def test_new_marker_is_a_change(history, data):
    history.push(AddMarkerCommand(data, 3, "Silo", "All"))

    assert history.changes.changed_node_ids == {3}
