from autodrive_editor.editing.commands.replace_network import ReplaceNetworkCommand
from autodrive_editor.model.autodrive_data import AutoDriveData, MarkerData, NodeData


def network(*positions, marker=None):
    data = AutoDriveData()
    for node_id, x in enumerate(positions, start=1):
        data.add_node(NodeData(node_id, x, 0, 0))
    if marker:
        data.add_marker(MarkerData(1, marker, "All"))
    return data


def test_replaces_nodes_and_markers_in_the_same_data_and_undoes_it():
    data = network(0, 10, marker="Hof")
    old_node = data.nodes[1]
    command = ReplaceNetworkCommand(data, network(5, 6, 7, marker="Feld"), "Load route")

    change = command.apply()

    assert [node.x for node in data.nodes.values()] == [5, 6, 7]
    assert [marker.name for marker in data.markers.values()] == ["Feld"]
    assert change.removed_node_ids == {1, 2}
    assert change.added_node_ids == {1, 2, 3}

    command.revert()

    assert data.nodes[1] is old_node
    assert [marker.name for marker in data.markers.values()] == ["Hof"]
