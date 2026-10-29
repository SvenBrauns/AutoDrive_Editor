import pytest

from autodrive_editor.editing.commands.remove_references import RemoveReferencesCommand
from autodrive_editor.model.autodrive_data import AutoDriveData, NodeData


@pytest.fixture
def data():
    data = AutoDriveData()
    data.add_node(NodeData(1, 0, 0, 0, outgoing={2, 99}, incoming={1}))
    data.add_node(NodeData(2, 5, 0, 0, incoming={1, 42}))
    return data


def test_removes_and_restores_the_entries(data):
    command = RemoveReferencesCommand(
        data, [(1, "outgoing", 99), (1, "incoming", 1), (2, "incoming", 42)]
    )

    change = command.apply()

    assert (data.nodes[1].outgoing, data.nodes[1].incoming) == ({2}, set())
    assert data.nodes[2].incoming == {1}
    assert change.connection_node_ids == {1, 2}
    assert command.text() == "Remove 3 invalid connection references"

    command.revert()

    assert (data.nodes[1].outgoing, data.nodes[1].incoming) == ({2, 99}, {1})
    assert data.nodes[2].incoming == {1, 42}


def test_rejects_missing_entries(data):
    with pytest.raises(ValueError):
        RemoveReferencesCommand(data, [(2, "outgoing", 1)])

    with pytest.raises(ValueError):
        RemoveReferencesCommand(data, [])
