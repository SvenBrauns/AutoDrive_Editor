import pytest

from autodrive.models import AutoDriveData, NodeData
from editing.set_connection_command import (
    CONNECTION_STATES,
    NO_CONNECTION,
    SetConnectionCommand,
    read_connection_state,
)
from rendering.connection_data import ConnectionType
from rendering.connection_geometry import get_connection_type


@pytest.fixture
def data():
    autodrive_data = AutoDriveData()
    autodrive_data.add_node(NodeData(1, 0, 0, 0))
    autodrive_data.add_node(NodeData(2, 10, 0, 0))
    return autodrive_data


def connect(data, connection_type, source=1, target=2):
    command = SetConnectionCommand(data, source, target, CONNECTION_STATES[connection_type])
    command.redo()
    return command


@pytest.mark.parametrize("connection_type", list(ConnectionType))
def test_created_connection_has_the_requested_type(data, connection_type):
    connect(data, connection_type)

    assert get_connection_type(data.nodes[1], data.nodes[2]) == connection_type
    assert data.validate_connections() == []


def test_regular_sets_outgoing_and_incoming(data):
    connect(data, ConnectionType.REGULAR)

    assert data.nodes[1].outgoing == {2}
    assert data.nodes[2].incoming == {1}
    assert data.nodes[1].incoming == set()
    assert data.nodes[2].outgoing == set()


def test_reverse_only_sets_source_outgoing(data):
    connect(data, ConnectionType.REVERSE)

    assert data.nodes[1].outgoing == {2}
    assert data.nodes[2].incoming == set()


def test_dual_sets_all_four_entries(data):
    connect(data, ConnectionType.DUAL)

    assert read_connection_state(data, 1, 2) == (True, True, True, True)


def test_changing_type_replaces_connection(data):
    connect(data, ConnectionType.DUAL)

    command = connect(data, ConnectionType.REGULAR)

    assert read_connection_state(data, 1, 2) == CONNECTION_STATES[ConnectionType.REGULAR]
    assert command.text() == "Connection ändern"


def test_undo_restores_previous_state(data):
    connect(data, ConnectionType.REVERSE)
    command = connect(data, ConnectionType.DUAL)

    command.undo()

    assert read_connection_state(data, 1, 2) == CONNECTION_STATES[ConnectionType.REVERSE]


def test_remove_connection(data):
    connect(data, ConnectionType.REGULAR)

    command = SetConnectionCommand(data, 1, 2, NO_CONNECTION)
    command.redo()

    assert read_connection_state(data, 1, 2) == NO_CONNECTION
    assert command.text() == "Connection entfernen"


def test_other_connections_are_untouched(data):
    data.add_node(NodeData(3, 20, 0, 0, incoming={1}))
    data.nodes[1].outgoing.add(3)

    connect(data, ConnectionType.DUAL)

    assert 3 in data.nodes[1].outgoing
    assert data.nodes[3].incoming == {1}


def test_unchanged_state_is_obsolete(data):
    connect(data, ConnectionType.REGULAR)

    command = SetConnectionCommand(data, 1, 2, CONNECTION_STATES[ConnectionType.REGULAR])

    assert command.isObsolete()


def test_reports_both_nodes(data):
    changes = []
    command = SetConnectionCommand(data, 1, 2, CONNECTION_STATES[ConnectionType.DUAL])
    command.set_change_listener(changes.append)

    command.redo()

    assert changes[0].connection_node_ids == {1, 2}


def test_rejects_self_connection_and_unknown_nodes(data):
    with pytest.raises(ValueError):
        SetConnectionCommand(data, 1, 1, NO_CONNECTION)

    with pytest.raises(ValueError):
        SetConnectionCommand(data, 1, 99, NO_CONNECTION)
