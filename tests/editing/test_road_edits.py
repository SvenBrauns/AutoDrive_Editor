import copy

import pytest

from autodrive_editor.editing.road_edits import split_connection
from autodrive_editor.model.autodrive_data import SUBPRIO_FLAG, AutoDriveData, NodeData
from autodrive_editor.model.connections import ConnectionType, get_connection_type


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
