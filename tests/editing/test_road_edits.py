import copy

import pytest

from autodrive_editor.editing.commands.delete_nodes import DeleteAndReconnectCommand
from autodrive_editor.editing.road_edits import ReconnectError, plan_reconnect, split_connection
from autodrive_editor.model.autodrive_data import SUBPRIO_FLAG, AutoDriveData, NodeData
from autodrive_editor.model.connections import (
    CONNECTION_STATES,
    ConnectionType,
    get_connection_type,
    write_connection_state,
)


@pytest.fixture
def data():
    """1 -> 2 regular (height 0 to 10), 2 <-> 3 dual, 3 -> 4 reverse."""

    autodrive_data = AutoDriveData()
    autodrive_data.add_node(NodeData(1, 0, 0, 0, outgoing={2}))
    autodrive_data.add_node(NodeData(2, 10, 10, 0, incoming={1, 3}, outgoing={3}))
    autodrive_data.add_node(NodeData(3, 20, 0, 0, incoming={2}, outgoing={2, 4}))
    autodrive_data.add_node(NodeData(4, 30, 0, 0))
    return autodrive_data


@pytest.mark.parametrize(
    ("source", "target", "connection_type"),
    [(1, 2, ConnectionType.REGULAR), (2, 3, ConnectionType.DUAL), (3, 4, ConnectionType.REVERSE)],
)
def test_split_keeps_type_and_direction_on_both_halves(data, source, target, connection_type):
    x = (data.nodes[source].x + data.nodes[target].x) / 2
    split_connection(data, source, target, x, 3, node_id=5, flag=0).redo()

    nodes = data.nodes
    assert target not in nodes[source].outgoing | nodes[source].incoming
    assert get_connection_type(nodes[source], nodes[5]) == connection_type
    assert get_connection_type(nodes[5], nodes[target]) == connection_type
    assert data.validate_connections() == []


def test_split_puts_node_on_the_line_with_height_between_the_ends(data):
    split_connection(data, 1, 2, 2.5, 4, node_id=5, flag=SUBPRIO_FLAG).redo()

    node = data.nodes[5]
    assert (node.x, node.y, node.z, node.flag) == (2.5, 2.5, 0, SUBPRIO_FLAG)


def test_split_is_undone_in_one_step(data):
    before = copy.deepcopy(data.nodes)
    command = split_connection(data, 2, 3, 15, 0, node_id=5, flag=0)

    command.redo()
    command.undo()

    assert data.nodes == before


# --- delete and reconnect ---------------------------------------------------


def connect(data, source, target, connection_type):
    write_connection_state(data, source, target, CONNECTION_STATES[connection_type])


@pytest.fixture
def road():
    """1 -> 2 -> 3 -> 4 regular, 4 <-> 5 <-> 6 dual, 6 -> 7 -> 8 reverse, 9 -> 3 (3 is a
    junction), 10 -> 11 -> 12 and 10 -> 12 (a triangle)."""

    data = AutoDriveData()

    for node_id in range(1, 13):
        data.add_node(NodeData(node_id, node_id * 10, 0, 0))

    for source, target, connection_type in [
        (1, 2, ConnectionType.REGULAR),
        (2, 3, ConnectionType.REGULAR),
        (3, 4, ConnectionType.REGULAR),
        (9, 3, ConnectionType.REGULAR),
        (4, 5, ConnectionType.DUAL),
        (5, 6, ConnectionType.DUAL),
        (6, 7, ConnectionType.REVERSE),
        (7, 8, ConnectionType.REVERSE),
        (10, 11, ConnectionType.REGULAR),
        (11, 12, ConnectionType.REGULAR),
        (10, 12, ConnectionType.REGULAR),
    ]:
        connect(data, source, target, connection_type)

    return data


@pytest.mark.parametrize(
    ("node_ids", "source", "target", "connection_type"),
    [
        ({2}, 1, 3, ConnectionType.REGULAR),
        ({5}, 4, 6, ConnectionType.DUAL),
        ({7}, 6, 8, ConnectionType.REVERSE),
    ],
)
def test_reconnect_joins_the_ends_with_the_same_type(
    road, node_ids, source, target, connection_type
):
    command = DeleteAndReconnectCommand(road, node_ids, plan_reconnect(road, node_ids))
    command.redo()

    nodes = road.nodes
    assert target in nodes[source].outgoing
    assert get_connection_type(nodes[source], nodes[target]) == connection_type
    assert road.validate_connections() == []


def test_reconnect_a_run_of_nodes_and_undo(road):
    road.add_node(NodeData(13, 0, 0, 10))
    connect(road, 8, 13, ConnectionType.REVERSE)
    before = copy.deepcopy(road.nodes)
    command = DeleteAndReconnectCommand(road, {7, 8}, plan_reconnect(road, {7, 8}))

    assert command.connections[0][:2] in [(6, 13), (13, 6)]
    command.redo()
    command.undo()

    assert road.nodes == before


@pytest.mark.parametrize(
    ("node_ids", "message"),
    [
        ({3}, "Node 3 is a junction or a road end"),
        ({1}, "Node 1 is a junction or a road end"),
        ({4}, "The connections at node 4 differ in type or direction"),
        ({11}, "Nodes 10 and 12 are already connected"),
    ],
)
def test_reconnect_is_refused(road, node_ids, message):
    with pytest.raises(ReconnectError, match=message):
        plan_reconnect(road, node_ids)


def test_reconnect_refuses_a_whole_ring():
    data = AutoDriveData()

    for node_id in (1, 2, 3):
        data.add_node(NodeData(node_id, node_id, 0, 0))

    for source, target in [(1, 2), (2, 3), (3, 1)]:
        connect(data, source, target, ConnectionType.REGULAR)

    with pytest.raises(ReconnectError, match="closed ring"):
        plan_reconnect(data, {1, 2, 3})
