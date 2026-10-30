from autodrive_editor.editing.join_rules import join_problem
from autodrive_editor.model.autodrive_data import AutoDriveData, MarkerData, NodeData
from autodrive_editor.model.connections import CONNECTION_STATES, write_connection_state


def road_data():
    """A one-way road 1 → 2 → 3."""

    data = AutoDriveData()

    for node_id in (1, 2, 3):
        data.add_node(NodeData(node_id, node_id * 10, 0, 0))

    write_connection_state(data, 1, 2, CONNECTION_STATES["regular"])
    write_connection_state(data, 2, 3, CONNECTION_STATES["regular"])

    return data


def test_through_road_node_fits_as_start_end_and_on_the_way():
    data = road_data()

    assert join_problem(data, 2, starts=True, ends=False) is None
    assert join_problem(data, 2, starts=False, ends=True) is None
    assert join_problem(data, 2, starts=False, ends=False) is None


def test_continuing_the_end_of_a_road_is_fine_but_not_ending_there():
    data = road_data()

    assert join_problem(data, 3, starts=True, ends=False) is None
    assert "leads nowhere" in join_problem(data, 3, starts=False, ends=True)


def test_start_of_a_road_cannot_be_reached():
    data = road_data()

    assert "Nothing drives to node 1" in join_problem(data, 1, starts=True, ends=False)
    assert join_problem(data, 1, starts=False, ends=True) is None


def test_marker_node_never_fits():
    data = road_data()
    data.add_marker(MarkerData(2, "Silo"))

    assert "marker" in join_problem(data, 2, starts=False, ends=False)
