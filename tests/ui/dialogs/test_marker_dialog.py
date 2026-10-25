from autodrive_editor.ui.dialogs.marker_dialog import MarkerDialog


def dialog(name="", group="All", groups=("All", "Felder"), taken=("Hof",)):
    return MarkerDialog("Marker hinzufügen", name, group, list(groups), set(taken))


def test_name_is_required(qapp):
    marker_dialog = dialog()

    assert not marker_dialog.is_valid
    assert marker_dialog.hint_label.text() == MarkerDialog.EMPTY_NAME_TEXT


def test_names_of_other_markers_are_refused(qapp):
    marker_dialog = dialog()

    marker_dialog.name_input.setText("Hof")

    assert not marker_dialog.is_valid
    assert marker_dialog.hint_label.text() == MarkerDialog.TAKEN_NAME_TEXT


def test_values_are_trimmed(qapp):
    marker_dialog = dialog()

    marker_dialog.name_input.setText("  Silo ")
    marker_dialog.group_input.setCurrentText(" Felder ")

    assert marker_dialog.is_valid
    assert marker_dialog.values == ("Silo", "Felder")


def test_new_group_is_announced(qapp):
    marker_dialog = dialog(name="Silo")

    marker_dialog.group_input.setCurrentText("Lager")

    assert marker_dialog.is_valid
    assert "Lager" in marker_dialog.hint_label.text()


def test_group_is_required(qapp):
    marker_dialog = dialog(name="Silo")

    marker_dialog.group_input.setCurrentText("")

    assert not marker_dialog.is_valid


def test_groups_are_listed_alphabetically(qapp):
    marker_dialog = dialog(groups=("Zuletzt", "All", "felder"))

    items = [
        marker_dialog.group_input.itemText(i) for i in range(marker_dialog.group_input.count())
    ]
    assert items == ["All", "felder", "Zuletzt"]
