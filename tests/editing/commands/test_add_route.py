import pytest

from autodrive_editor.editing.commands.add_route import AddRouteCommand
from autodrive_editor.model.autodrive_data import AutoDriveData, NodeData
from autodrive_editor.model.connections import (
    CONNECTION_STATES,
    ConnectionType,
    get_connection_type,
    write_connection_state,
)

REGULAR = CONNECTION_STATES[ConnectionType.REGULAR]
DUAL = CONNECTION_STATES[ConnectionType.DUAL]


@pytest.fixture
def data():
    data = AutoDriveData()
    data.add_node(NodeData(1, 0, 0, 0))
    data.add_node(NodeData(2, 10, 0, 0))
    write_connection_state(data, 1, 2, REGULAR)
    return data


def test_adds_nodes_and_sets_each_connection_and_undoes_it(data):
    command = AddRouteCommand(
        "Find route", data, [NodeData(3, 5, 0, 5)], [(2, 1, DUAL), (1, 3, REGULAR)]
    )

    change = command.apply()

    assert change.added_node_ids == {3}
    assert change.connection_node_ids == {1, 2}
    assert get_connection_type(data.nodes[1], data.nodes[2]) == ConnectionType.DUAL
    assert 3 in data.nodes[1].outgoing
    assert data.validate_connections() == []

    command.revert()

    assert 3 not in data.nodes
    assert data.nodes[1].outgoing == {2} and data.nodes[2].incoming == {1}
    assert data.nodes[2].outgoing == set() and data.nodes[1].incoming == set()


def test_rejects_unknown_nodes_and_used_ids(data):
    with pytest.raises(ValueError):
        AddRouteCommand("x", data, [], [(1, 9, REGULAR)])

    with pytest.raises(ValueError):
        AddRouteCommand("x", data, [NodeData(2, 0, 0, 0)], [])
