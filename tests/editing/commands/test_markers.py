import copy

import pytest

from autodrive_editor.editing.commands.markers import (
    AddMarkerCommand,
    DeleteMarkerCommand,
    DeleteMarkerGroupCommand,
    EditMarkerCommand,
    MoveMarkerCommand,
    RenameMarkerGroupCommand,
)
from autodrive_editor.model.autodrive_data import AutoDriveData, MarkerData, MarkerGroup, NodeData


@pytest.fixture
def data():
    """Nodes 1-5; markers Hof (1), Silo (2), Feld 7 (3) in this order."""

    autodrive_data = AutoDriveData()
    for node_id in range(1, 6):
        autodrive_data.add_node(NodeData(node_id, node_id * 10, 0, 0))
    autodrive_data.marker_groups = [MarkerGroup("All", 1), MarkerGroup("Felder", 2)]
    autodrive_data.add_marker(MarkerData(1, "Hof", "All"))
    autodrive_data.add_marker(MarkerData(2, "Silo", "All"))
    autodrive_data.add_marker(MarkerData(3, "Feld 7", "Felder"))
    return autodrive_data


def snapshot(data):
    return copy.deepcopy((list(data.markers.items()), data.marker_groups))


def names(data):
    return [marker.name for marker in data.markers.values()]


def test_new_marker_is_added_at_the_end(data):
    change = AddMarkerCommand(data, 4, "Werkstatt", "All").apply()

    assert names(data) == ["Hof", "Silo", "Feld 7", "Werkstatt"]
    assert change.changed_marker_node_ids == {4}
    assert not change.marker_groups_changed


def test_new_group_is_created_with_next_id_and_removed_on_undo(data):
    before = snapshot(data)
    command = AddMarkerCommand(data, 4, "Wiese", "Weiden")

    assert command.apply().marker_groups_changed
    assert data.find_marker_group("Weiden").group_id == 3

    command.revert()
    assert snapshot(data) == before


def test_groups_without_ids_get_no_id(data):
    data.marker_groups = [MarkerGroup("All")]

    AddMarkerCommand(data, 4, "Wiese", "Weiden").apply()

    assert data.find_marker_group("Weiden").group_id is None


def test_marker_on_marked_node_is_rejected(data):
    with pytest.raises(ValueError):
        AddMarkerCommand(data, 1, "Doppelt", "All")


def test_edit_changes_name_and_group_and_undo_restores(data):
    before = snapshot(data)
    command = EditMarkerCommand(data, 2, "Silo Nord", "Lager")

    command.apply()
    assert data.markers[2].name == "Silo Nord"
    assert data.markers[2].group == "Lager"
    assert data.find_marker_group("Lager") is not None

    command.revert()
    assert snapshot(data) == before


def test_unchanged_edit_is_obsolete(data):
    assert EditMarkerCommand(data, 2, "Silo", "All").isObsolete()


def test_delete_and_undo_keep_the_marker_number(data):
    command = DeleteMarkerCommand(data, 2)

    command.apply()
    assert names(data) == ["Hof", "Feld 7"]
    assert 2 in data.nodes

    command.revert()
    assert names(data) == ["Hof", "Silo", "Feld 7"]


def test_move_keeps_number_name_and_group(data):
    before = snapshot(data)
    command = MoveMarkerCommand(data, 2, 5)

    change = command.apply()
    assert list(data.markers) == [1, 5, 3]
    assert data.markers[5].name == "Silo"
    assert data.markers[5].node_id == 5
    assert change.changed_marker_node_ids == {2, 5}

    command.revert()
    assert snapshot(data) == before


def test_move_onto_marked_node_is_rejected(data):
    with pytest.raises(ValueError):
        MoveMarkerCommand(data, 2, 3)


def test_rename_group_moves_markers_along(data):
    before = snapshot(data)
    command = RenameMarkerGroupCommand(data, "All", "Hof und Lager")

    command.apply()
    assert data.find_marker_group("Hof und Lager").group_id == 1
    assert data.markers[1].group == data.markers[2].group == "Hof und Lager"
    assert data.markers[3].group == "Felder"

    command.revert()
    assert snapshot(data) == before


def test_rename_works_for_groups_only_named_on_markers(data):
    data.marker_groups = []

    RenameMarkerGroupCommand(data, "Felder", "Äcker").apply()

    assert data.markers[3].group == "Äcker"


def test_rename_to_existing_group_is_rejected(data):
    with pytest.raises(ValueError):
        RenameMarkerGroupCommand(data, "All", "Felder")


def test_only_empty_groups_can_be_deleted(data):
    with pytest.raises(ValueError):
        DeleteMarkerGroupCommand(data, "Felder")

    data.marker_groups.insert(1, MarkerGroup("Leer", 3))
    before = snapshot(data)
    command = DeleteMarkerGroupCommand(data, "Leer")

    command.apply()
    assert [group.name for group in data.marker_groups] == ["All", "Felder"]

    command.revert()
    assert snapshot(data) == before


def test_group_names_include_groups_only_on_markers(data):
    data.marker_groups = [MarkerGroup("All", 1)]

    assert data.marker_group_names() == ["All", "Felder"]
