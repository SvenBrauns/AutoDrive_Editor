from autodrive_editor.model.autodrive_data import AutoDriveData, NodeData
from autodrive_editor.model.connections import (
    NO_CONNECTION,
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
