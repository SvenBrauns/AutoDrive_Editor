from autodrive_editor.model.autodrive_data import AutoDriveData, NodeData
from autodrive_editor.project.route_match import same_network


def network(*xs):
    data = AutoDriveData()
    for node_id, x in enumerate(xs, start=1):
        data.add_node(NodeData(node_id, x, 1.0, 2.0))
    return data


def test_same_positions_in_any_order_with_route_rounding_are_the_same_network():
    assert same_network(network(1.234, 5.0), network(5.0, 1.23))


def test_other_count_or_position_is_another_network():
    assert not same_network(network(1.0, 5.0), network(1.0))
    assert not same_network(network(1.0, 5.0), network(1.0, 5.5))
