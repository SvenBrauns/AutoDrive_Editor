import pytest

from autodrive_editor.model.autodrive_data import SUBPRIO_FLAG, AutoDriveData, NodeData
from autodrive_editor.model.connections import (
    NO_CONNECTION,
    ConnectionType,
    is_subprio_connection,
    read_connection_state,
    write_connection_state,
)


def test_write_connection_state_sets_and_clears_all_four_entries():
    data = AutoDriveData()
    for node_id in (1, 2, 3):
        data.add_node(NodeData(node_id, node_id, 0, 0))
    data.nodes[1].outgoing.add(3)

    write_connection_state(data, 1, 2, (True, False, False, True))

    assert read_connection_state(data, 1, 2) == (True, False, False, True)
    assert data.nodes[1].outgoing == {2, 3}

    write_connection_state(data, 1, 2, NO_CONNECTION)

    assert read_connection_state(data, 1, 2) == NO_CONNECTION
    assert data.nodes[1].outgoing == {3}


@pytest.mark.parametrize(
    ("source_flag", "target_flag", "connection_type", "expected"),
    [
        (0, 0, ConnectionType.REGULAR, False),
        (0, SUBPRIO_FLAG, ConnectionType.REGULAR, True),
        (SUBPRIO_FLAG, 0, ConnectionType.REGULAR, False),
        (SUBPRIO_FLAG, 0, ConnectionType.REVERSE, False),
        (0, SUBPRIO_FLAG, ConnectionType.REVERSE, True),
        (SUBPRIO_FLAG, 0, ConnectionType.DUAL, True),
        (0, SUBPRIO_FLAG, ConnectionType.DUAL, True),
        (0, 0, ConnectionType.DUAL, False),
    ],
)
def test_subprio_connection_depends_on_the_target_and_for_dual_on_both_ends(
    source_flag, target_flag, connection_type, expected
):
    source = NodeData(1, 0, 0, 0, flag=source_flag)
    target = NodeData(2, 1, 0, 0, flag=target_flag)

    assert is_subprio_connection(source, target, connection_type) == expected
