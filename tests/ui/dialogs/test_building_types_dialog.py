from PySide6.QtCore import Qt

from autodrive_editor.file_io.savegame_buildings import BuildingGroup, BuildingType
from autodrive_editor.ui.dialogs.building_types_dialog import GROUP, BuildingTypesDialog

TYPES = [
    BuildingType("$data/barn.xml", "Barn", "sheds", BuildingGroup.SHEDS, 2),
    BuildingType("$data/garage.xml", "Garage", "sheds", BuildingGroup.SHEDS, 1),
    BuildingType("$data/silo.xml", "Silo", "silos", BuildingGroup.STATIONS, 1),
]

STATES = {Qt.CheckState.Checked: "on", Qt.CheckState.Unchecked: "off"}


def rows(dialog):
    """(text, file, count, check state, group choice) of the shown groups and, indented, their
    types."""

    rows = []

    for i in range(dialog.table.topLevelItemCount()):
        group = dialog.table.topLevelItem(i)

        if group.isHidden():
            continue

        for item in [group] + [group.child(j) for j in range(group.childCount())]:
            indent = "" if item is group else "  "
            state = STATES.get(item.checkState(0), "partly")
            choice = dialog.table.itemWidget(item, GROUP)
            rows.append(
                (indent + item.text(0), item.text(2), item.text(3), state)
                + ((choice.currentText(),) if choice else ())
            )

    return rows


def test_types_are_listed_by_group_with_count_and_hidden_ones_unticked(qapp):
    dialog = BuildingTypesDialog(TYPES, {}, {"$data/garage.xml"})

    assert rows(dialog) == [
        ("Stations", "", "", "on"),
        ("  Silo", "silo.xml", "1", "on", "Stations"),
        ("Sheds", "", "", "partly"),
        ("  Barn", "barn.xml", "2", "on", "Sheds"),
        ("  Garage", "garage.xml", "1", "off", "Sheds"),
    ]


def test_types_moved_by_the_user_are_in_their_new_group(qapp):
    dialog = BuildingTypesDialog(TYPES, {"$data/silo.xml": BuildingGroup.OTHER}, set())

    assert rows(dialog)[-2:] == [
        ("Other", "", "", "on"),
        ("  Silo", "silo.xml", "1", "on", "Other"),
    ]


def test_choosing_a_group_moves_the_type(qapp):
    dialog = BuildingTypesDialog(TYPES, {}, {"$data/silo.xml"})

    dialog.table.itemWidget(dialog._items()[0], GROUP).setCurrentIndex(1)

    assert rows(dialog) == [
        ("Sheds", "", "", "partly"),
        ("  Barn", "barn.xml", "2", "on", "Sheds"),
        ("  Garage", "garage.xml", "1", "on", "Sheds"),
        ("  Silo", "silo.xml", "1", "off", "Sheds"),
    ]
    assert dialog.groups == {"$data/silo.xml": BuildingGroup.SHEDS}


def test_only_groups_that_differ_from_the_own_one_are_kept(qapp):
    groups = {"$data/silo.xml": BuildingGroup.SHEDS, "$data/other.xml": BuildingGroup.OTHER}
    dialog = BuildingTypesDialog(TYPES, groups, set())

    dialog.set_group(dialog._items()[-1], BuildingGroup.STATIONS)

    # The type of another map keeps its group.
    assert dialog.groups == {"$data/other.xml": BuildingGroup.OTHER}


def test_unticking_a_group_hides_all_its_types(qapp):
    dialog = BuildingTypesDialog(TYPES, {}, set())

    dialog.table.topLevelItem(1).setCheckState(0, Qt.CheckState.Unchecked)

    assert dialog.hidden_types == {"$data/barn.xml", "$data/garage.xml"}


def test_unticked_types_and_hidden_types_of_other_maps_are_hidden(qapp):
    dialog = BuildingTypesDialog(TYPES, {}, {"$data/silo.xml", "$data/other.xml"})

    dialog.table.topLevelItem(0).child(0).setCheckState(0, Qt.CheckState.Checked)
    dialog.table.topLevelItem(1).child(0).setCheckState(0, Qt.CheckState.Unchecked)

    assert dialog.hidden_types == {"$data/barn.xml", "$data/other.xml"}


def test_show_all_and_hide_all(qapp):
    dialog = BuildingTypesDialog(TYPES, {}, {"$data/silo.xml"})

    dialog._check_all(Qt.CheckState.Unchecked)
    assert dialog.hidden_types == {"$data/barn.xml", "$data/garage.xml", "$data/silo.xml"}

    dialog._check_all(Qt.CheckState.Checked)
    assert dialog.hidden_types == set()
