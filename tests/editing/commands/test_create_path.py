import pytest

from autodrive_editor.editing.commands.create_path import CreatePathCommand
from autodrive_editor.model.autodrive_data import AutoDriveData, NodeData
from autodrive_editor.model.connections import (
    CONNECTION_STATES,
    ConnectionType,
    read_connection_state,
)

REGULAR = CONNECTION_STATES[ConnectionType.REGULAR]
DUAL = CONNECTION_STATES[ConnectionType.DUAL]


@pytest.fixture
def data():
    autodrive_data = AutoDriveData()
    autodrive_data.add_node(NodeData(1, 0, 0, 0))
    autodrive_data.add_node(NodeData(2, 30, 0, 0))
    return autodrive_data


def new_nodes(*ids):
    return [NodeData(node_id, node_id * 10, 0, 5, flag=1) for node_id in ids]


def test_new_nodes_are_added_and_chained(data):
    command = CreatePathCommand("Linie", data, [3, 4, 5], new_nodes(3, 4, 5), REGULAR)

    command.redo()

    assert set(data.nodes) == {1, 2, 3, 4, 5}
    assert data.nodes[3].outgoing == {4}
    assert data.nodes[4].incoming == {3}
    assert data.nodes[4].outgoing == {5}
    assert data.nodes[3].incoming == set()
    assert data.validate_connections() == []


def test_undo_and_redo(data):
    command = CreatePathCommand("Linie", data, [3, 4], new_nodes(3, 4), DUAL)
    command.redo()

    command.undo()
    assert set(data.nodes) == {1, 2}

    command.redo()
    assert read_connection_state(data, 3, 4) == DUAL


def test_chain_between_existing_nodes(data):
    command = CreatePathCommand("Linie", data, [1, 3, 2], new_nodes(3), REGULAR)

    command.redo()

    assert data.nodes[1].outgoing == {3}
    assert data.nodes[3].outgoing == {2}
    assert data.nodes[2].incoming == {3}

    command.undo()

    assert set(data.nodes) == {1, 2}
    assert data.nodes[1].outgoing == data.nodes[2].incoming == set()


def test_undo_restores_existing_connection_between_two_existing_nodes(data):
    reverse = CONNECTION_STATES[ConnectionType.REVERSE]
    data.nodes[1].outgoing.add(2)
    command = CreatePathCommand("Linie", data, [1, 2], [], DUAL)

    command.redo()
    assert read_connection_state(data, 1, 2) == DUAL

    command.undo()
    assert read_connection_state(data, 1, 2) == reverse
    assert data.nodes[2].incoming == set()


def test_data_change_contents(data):
    changes = []
    command = CreatePathCommand("Linie", data, [1, 3, 2], new_nodes(3), REGULAR)
    command.set_change_listener(changes.append)

    command.redo()
    command.undo()

    assert changes[0].added_node_ids == {3}
    assert changes[0].connection_node_ids == {1, 2}
    assert changes[1].removed_node_ids == {3}
    assert changes[1].connection_node_ids == {1, 2}


@pytest.mark.parametrize(
    ("chain", "nodes"),
    [
        ([3], new_nodes(3)),
        ([3, 3], new_nodes(3)),
        ([1, 2, 9], []),
        ([2, 3], new_nodes(2, 3)),
    ],
)
def test_invalid_chains_are_rejected(data, chain, nodes):
    with pytest.raises(ValueError):
        CreatePathCommand("Linie", data, chain, nodes, REGULAR)
