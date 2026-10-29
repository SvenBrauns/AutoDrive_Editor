from PySide6.QtCore import Qt

from autodrive_editor.file_io.savegame_sheds import IndoorArea
from autodrive_editor.ui.dialogs.shed_types_dialog import ShedTypesDialog

CORNERS = ((0, 0), (10, 0), (10, 10), (0, 10))
AREAS = [
    IndoorArea("$data/barn.xml", "a", CORNERS, 0.0, "Barn", "sheds"),
    IndoorArea("$data/barn.xml", "b", CORNERS, 0.0, "Barn", "sheds"),
    IndoorArea("$data/garage.xml", "c", CORNERS, 0.0, "Garage", "sheds"),
    IndoorArea("$data/beehive.xml", "d", CORNERS, 0.0, "Beehive", "beeHives"),
]

STATES = {Qt.CheckState.Checked: "on", Qt.CheckState.Unchecked: "off"}


def rows(dialog):
    """(text, file, count, check state) of the categories and, indented, their types."""

    rows = []

    for i in range(dialog.table.topLevelItemCount()):
        category = dialog.table.topLevelItem(i)

        for item in [category] + [category.child(j) for j in range(category.childCount())]:
            indent = "" if item is category else "  "
            state = STATES.get(item.checkState(0), "partly")
            rows.append((indent + item.text(0), item.text(1), item.text(2), state))

    return rows


def test_types_are_listed_by_category_with_count_and_hidden_ones_unticked(qapp):
    dialog = ShedTypesDialog(AREAS, {"$data/garage.xml"})

    assert rows(dialog) == [
        ("Beehives", "", "1", "on"),
        ("  Beehive", "beehive.xml", "1", "on"),
        ("Vehicle sheds", "", "3", "partly"),
        ("  Barn", "barn.xml", "2", "on"),
        ("  Garage", "garage.xml", "1", "off"),
    ]


def test_unticking_a_category_hides_all_its_types(qapp):
    dialog = ShedTypesDialog(AREAS, set())

    dialog.table.topLevelItem(1).setCheckState(0, Qt.CheckState.Unchecked)

    assert dialog.hidden_types == {"$data/barn.xml", "$data/garage.xml"}


def test_unticked_types_and_hidden_types_of_other_maps_are_hidden(qapp):
    dialog = ShedTypesDialog(AREAS, {"$data/beehive.xml", "$data/other.xml"})

    dialog.table.topLevelItem(0).child(0).setCheckState(0, Qt.CheckState.Checked)
    dialog.table.topLevelItem(1).child(0).setCheckState(0, Qt.CheckState.Unchecked)

    assert dialog.hidden_types == {"$data/barn.xml", "$data/other.xml"}


def test_show_all_and_hide_all(qapp):
    dialog = ShedTypesDialog(AREAS, {"$data/beehive.xml"})

    dialog._check_all(Qt.CheckState.Unchecked)
    assert dialog.hidden_types == {"$data/barn.xml", "$data/beehive.xml", "$data/garage.xml"}

    dialog._check_all(Qt.CheckState.Checked)
    assert dialog.hidden_types == set()
