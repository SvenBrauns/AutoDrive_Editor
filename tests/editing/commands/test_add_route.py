import pytest

from autodrive_editor.editing.commands.add_route import AddRouteCommand
from autodrive_editor.model.autodrive_data import AutoDriveData, MarkerData, NodeData
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


def test_adds_markers_on_new_nodes_with_their_group_and_undoes_them(data):
    command = AddRouteCommand(
        "Stations", data, [NodeData(3, 5, 0, 5)], [(2, 3, REGULAR)], [MarkerData(3, "A", "New")]
    )

    change = command.apply()

    assert data.markers[3].name == "A"
    assert data.find_marker_group("New") is not None
    assert change.changed_marker_node_ids == {3}
    assert change.marker_groups_changed

    command.revert()

    assert 3 not in data.markers
    assert data.find_marker_group("New") is None


def test_a_marker_must_be_on_a_new_node(data):
    with pytest.raises(ValueError):
        AddRouteCommand("Stations", data, [], [], [MarkerData(1, "A", "New")])
