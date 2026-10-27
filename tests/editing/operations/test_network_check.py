import pytest

from autodrive_editor.editing.edit_context import EditContext
from autodrive_editor.editing.edit_history import EditHistory
from autodrive_editor.editing.operations.network_check import (
    NetworkCheckOperation,
    choose_kept_node,
    position_on_map,
)
from autodrive_editor.model.autodrive_data import AutoDriveData, MarkerData, NodeData


@pytest.fixture
def setup():
    """Nodes 1/2 and 3/4 overlap, node 5 lies outside the 2048 m map, node
    6 floats 20 m above the terrain (which is 1 m high everywhere)."""

    data = AutoDriveData()
    data.add_node(NodeData(1, 0, 0, 0, outgoing={2}))
    data.add_node(NodeData(2, 0, 0, 0, incoming={1}))
    data.add_node(NodeData(3, 50, 0, 0))
    data.add_node(NodeData(4, 50, 0, 0))
    data.add_node(NodeData(5, 1500, 7, -10))
    data.add_node(NodeData(6, 100, 21, 0))
    edits = EditHistory()
    terrain = {"height": 1.0}
    operation = NetworkCheckOperation(
        EditContext(edits, lambda: data, terrain_height_at=lambda x, z: terrain["height"]),
        map_scale=lambda: 1,
    )
    messages = []
    operation.status_changed.connect(messages.append)
    return data, edits, operation, terrain, messages


def test_kept_node_is_the_lowest_id():
    data = AutoDriveData()
    for node_id in (4, 7, 9):
        data.add_node(NodeData(node_id, 0, 0, 0))

    assert choose_kept_node(data, [9, 4, 7]) == 4


def test_kept_node_is_the_one_with_a_marker():
    data = AutoDriveData()
    for node_id in (4, 7, 9):
        data.add_node(NodeData(node_id, 0, 0, 0))
    data.add_marker(MarkerData(7, "Silo"))

    assert choose_kept_node(data, [4, 7, 9]) == 7

    data.add_marker(MarkerData(9, "Hof"))

    assert choose_kept_node(data, [4, 7, 9]) is None


def test_position_on_map_keeps_a_margin_from_the_border():
    assert position_on_map(1500, -10, 1, 1.0) == (1023, -10)
    assert position_on_map(-5000, 5000, 2, 1.0) == (-2047, 2047)
    assert position_on_map(10, 20, 1, 1.0) == (10, 20)


def test_merge_all_groups_is_one_undo_step(setup):
    data, edits, operation, _, messages = setup

    assert operation.merge_overlapping([[1, 2], [3, 4]])

    assert set(data.nodes) == {1, 3, 5, 6}
    assert messages == ["2 groups of overlapping nodes merged"]

    edits.undo()

    assert set(data.nodes) == {1, 2, 3, 4, 5, 6}


def test_merge_skips_groups_with_several_markers(setup):
    data, _, operation, _, messages = setup
    data.add_marker(MarkerData(3, "Silo"))
    data.add_marker(MarkerData(4, "Hof"))

    operation.merge_overlapping([[1, 2], [3, 4]])

    assert set(data.nodes) == {1, 3, 4, 5, 6}
    assert messages == [
        "Overlapping nodes merged – 1 skipped: several nodes of the group have a marker"
    ]


def test_merge_skips_nodes_deleted_since_the_check(setup):
    data, edits, operation, _, _ = setup
    del data.nodes[4]

    assert not operation.merge_overlapping([[3, 4]])
    assert not edits.can_undo


def test_move_onto_map_takes_the_terrain_height(setup):
    data, edits, operation, _, _ = setup

    assert operation.move_onto_map([5, 6])

    node = data.nodes[5]
    assert (node.x, node.y, node.z) == (1023, 1.0, -10)
    assert data.nodes[6].x == 100  # already on the map
    assert edits.undo_stack.undoText() == "Move node onto the map"


def test_move_onto_map_keeps_the_height_without_heightmap(setup):
    data, _, operation, terrain, _ = setup
    terrain["height"] = None

    operation.move_onto_map([5])

    assert data.nodes[5].y == 7


def test_set_heights_from_terrain(setup):
    data, edits, operation, _, messages = setup

    assert operation.set_heights_from_terrain([6, 99])

    assert data.nodes[6].y == 1.0
    assert messages == ["Node height set from the terrain"]

    edits.undo()

    assert data.nodes[6].y == 21


def test_nothing_changes_while_the_history_is_locked(setup):
    data, edits, operation, _, _ = setup
    edits.set_history_locked(True)

    assert not operation.merge_overlapping([[1, 2]])
    assert not operation.move_onto_map([5])
    assert not operation.set_heights_from_terrain([6])
    assert len(data.nodes) == 6
