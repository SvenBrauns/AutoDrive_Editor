import pytest

from autodrive_editor.model.autodrive_data import AutoDriveData, MarkerData, NodeData


def make_data(*node_ids):
    data = AutoDriveData()

    for node_id in node_ids:
        data.add_node(NodeData(node_id=node_id, x=0.0, y=0.0, z=0.0))

    return data


def test_flag_zero_is_regular_node():
    node = NodeData(node_id=1, x=0, y=0, z=0, flag=0)

    assert node.is_regular
    assert not node.is_subprio


def test_nonzero_flag_is_subprio_node():
    node = NodeData(node_id=1, x=0, y=0, z=0, flag=1)

    assert node.is_subprio
    assert not node.is_regular


@pytest.mark.parametrize("node_id", [0, -1])
def test_add_node_rejects_non_positive_id(node_id):
    with pytest.raises(ValueError):
        make_data(node_id)


def test_add_node_rejects_duplicate_id():
    data = make_data(1)

    with pytest.raises(ValueError):
        data.add_node(NodeData(node_id=1, x=0, y=0, z=0))


def test_add_marker_requires_existing_node():
    data = make_data(1)

    with pytest.raises(ValueError):
        data.add_marker(MarkerData(node_id=2, name="Hof"))


def test_get_sorted_nodes_orders_by_id():
    data = make_data(3, 1, 2)

    assert [node.node_id for node in data.get_sorted_nodes()] == [1, 2, 3]


def test_validate_connections_reports_unknown_targets():
    data = make_data(1, 2)
    data.nodes[1].outgoing = {2, 99}
    data.nodes[2].incoming = {1, 42}

    errors = data.validate_connections()

    assert len(errors) == 2
    assert any("99" in error for error in errors)
    assert any("42" in error for error in errors)


def test_validate_connections_is_empty_for_valid_network():
    data = make_data(1, 2)
    data.nodes[1].outgoing = {2}
    data.nodes[2].incoming = {1}

    assert data.validate_connections() == []


def test_clear_removes_nodes_and_markers():
    data = make_data(1)
    data.add_marker(MarkerData(node_id=1))

    data.clear()

    assert len(data) == 0
    assert data.markers == {}
