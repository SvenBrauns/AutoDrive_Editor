import pytest

from autodrive_editor.editing.clipboard import copy_nodes, nodes_for_paste
from autodrive_editor.editing.commands.paste_nodes import PasteNodesCommand
from autodrive_editor.model.autodrive_data import AutoDriveData, MarkerData, MarkerGroup, NodeData


@pytest.fixture
def data():
    """1 -> 2 -> 3 regular, marker "Tankstelle" (All) on 2."""

    autodrive_data = AutoDriveData()
    autodrive_data.add_node(NodeData(1, 0, 5, 0, outgoing={2}))
    autodrive_data.add_node(NodeData(2, 10, 6, 0, flag=1, incoming={1}, outgoing={3}))
    autodrive_data.add_node(NodeData(3, 20, 7, 10, incoming={2}))
    autodrive_data.marker_groups = [MarkerGroup("All", 1)]
    autodrive_data.add_marker(MarkerData(2, "Tankstelle", "All"))
    return autodrive_data


def test_copy_keeps_only_connections_inside(data):
    content = copy_nodes(data, {1, 2})

    assert [node.node_id for node in content.nodes] == [1, 2]
    assert content.nodes[1].outgoing == set()  # 2 -> 3 left out
    assert content.nodes[0].outgoing == {2}
    assert [marker.name for marker in content.markers] == ["Tankstelle"]


def test_copy_is_independent_of_later_edits(data):
    content = copy_nodes(data, {1})

    data.nodes[1].x = 99

    assert content.nodes[0].x == 0


def test_center_is_middle_of_bounding_box(data):
    assert copy_nodes(data, {1, 2, 3}).center == (10, 5)


def test_paste_gets_new_ids_offset_and_connections(data):
    nodes, _ = nodes_for_paste(copy_nodes(data, {1, 2}), data, offset=(100, 50))

    assert [(n.node_id, n.x, n.z, n.flag) for n in nodes] == [(4, 100, 50, 0), (5, 110, 50, 1)]
    assert nodes[0].outgoing == {5}
    assert nodes[1].incoming == {4}


def test_paste_uses_terrain_height_where_known(data):
    def height_at(x, z):
        return 42.0 if x < 105 else None

    nodes, _ = nodes_for_paste(copy_nodes(data, {1, 2}), data, (100, 0), height_at)

    assert [node.y for node in nodes] == [42.0, 6]


def test_marker_name_gets_a_number_in_the_same_group(data):
    content = copy_nodes(data, {2})

    _, markers = nodes_for_paste(content, data, (0, 0))
    assert markers[0].name == "Tankstelle (2)"

    data.add_node(NodeData(9, 0, 0, 0))
    data.add_marker(MarkerData(9, "Tankstelle (2)", "All"))
    _, markers = nodes_for_paste(content, data, (0, 0))
    assert markers[0].name == "Tankstelle (3)"


def test_marker_name_stays_when_free_in_its_group(data):
    content = copy_nodes(data, {2})
    data.markers[2].group = "Hof"

    _, markers = nodes_for_paste(content, data, (0, 0))

    assert markers[0].name == "Tankstelle"


def test_paste_command_adds_and_undo_removes_everything(data):
    content = copy_nodes(data, {2, 3})
    content.markers[0].group = "Neu"
    nodes, markers = nodes_for_paste(content, data, (0, 100))
    command = PasteNodesCommand(data, nodes, markers)

    change = command.apply()
    assert set(data.nodes) == {1, 2, 3, 4, 5}
    assert list(data.markers) == [2, 4]
    assert data.find_marker_group("Neu") is not None
    assert change.added_node_ids == {4, 5}

    change = command.revert()
    assert set(data.nodes) == {1, 2, 3}
    assert list(data.markers) == [2]
    assert data.find_marker_group("Neu") is None
    assert change.removed_node_ids == {4, 5}
