from autodrive_editor.editing.parking_layout import ParkingMode
from autodrive_editor.file_io.savegame_sheds import IndoorArea
from autodrive_editor.ui.dialogs.parking_spot_dialog import ParkingSpotDialog, compass_name

# 30 × 15 m; the front faces down (south) on the map.
SHED = IndoorArea("shed.xml", "1", ((-15, -7.5), (15, -7.5), (15, 7.5), (-15, 7.5)), 90.0)


def dialog(taken=()):
    parking_dialog = ParkingSpotDialog(SHED, ["Farm", "All"], set(taken))
    parking_dialog.group_input.setCurrentText("Farm")
    return parking_dialog


def test_defaults_open_a_long_side_with_bays_of_about_g1_width(qapp):
    settings = dialog().settings

    assert settings.mode == ParkingMode.BACK_IN
    assert settings.open_side == "front"
    assert settings.bays == 4
    assert settings.gaps == (0.0, 0.0, 0.0)
    assert settings.marker_name == "Shed"


def test_sides_show_their_compass_direction(qapp):
    parking_dialog = dialog()
    texts = [parking_dialog.side_input.itemText(i) for i in range(4)]

    assert texts == ["Front (south)", "Back (north)", "Left (west)", "Right (east)"]
    assert compass_name(44) == "north-east"


def test_too_narrow_bays_disable_create(qapp):
    parking_dialog = dialog()
    assert parking_dialog.is_valid

    parking_dialog.bays_input.setValue(10)

    assert not parking_dialog.is_valid
    assert (
        parking_dialog.bay_width_label.text()
        == f"{parking_dialog.locale().toString(2.9, 'f', 1)} m"
    )
    assert "red" in parking_dialog.bay_width_label.styleSheet()
    assert parking_dialog.preview.network is None


def test_marker_must_be_inside_the_shed(qapp):
    parking_dialog = dialog()

    parking_dialog.back_input.setValue(15.0)

    assert not parking_dialog.is_valid
    assert parking_dialog.hint_label.text() == "The marker must be inside the shed."


def test_taken_marker_names_are_refused(qapp):
    parking_dialog = dialog(taken={("Shed 3", "Farm")})

    assert not parking_dialog.is_valid

    parking_dialog.start_input.setValue(4)

    assert parking_dialog.is_valid


def test_name_and_group_are_required(qapp):
    parking_dialog = dialog()

    parking_dialog.group_input.setCurrentText(" ")
    assert parking_dialog.hint_label.text() == ParkingSpotDialog.EMPTY_GROUP_TEXT

    parking_dialog.name_input.setText("")
    assert parking_dialog.hint_label.text() == ParkingSpotDialog.EMPTY_NAME_TEXT
    assert not parking_dialog.is_valid


def test_new_group_is_announced(qapp):
    parking_dialog = dialog()

    parking_dialog.group_input.setCurrentText("Halle")

    assert parking_dialog.is_valid
    assert parking_dialog.hint_label.text() == "The group “Halle” will be created."


def test_drive_through_renames_the_side_fields(qapp):
    parking_dialog = dialog()

    parking_dialog.mode_input.setCurrentIndex(1)

    assert parking_dialog.side_label.text() == "Entry side:"
    assert parking_dialog.back_label.text() == "Exit offset:"
    assert parking_dialog.settings.mode == ParkingMode.DRIVE_THROUGH


def test_all_gaps_fill_every_gap_and_reset_restores_the_shed_settings(qapp):
    parking_dialog = dialog()

    parking_dialog.gap_input.setValue(0.4)
    parking_dialog.side_input.setCurrentIndex(2)
    parking_dialog.name_input.setText("Box")

    assert parking_dialog.settings.gaps == (0.4,) * (parking_dialog.settings.bays - 1)

    parking_dialog.reset_shed_settings()

    assert parking_dialog.settings.gaps == (0.0, 0.0, 0.0)
    assert parking_dialog.settings.open_side == "front"
    # Marker settings depend on the location and stay.
    assert parking_dialog.settings.marker_name == "Box"


def test_preview_paints_the_plan(qapp):
    parking_dialog = dialog()
    parking_dialog.preview.resize(400, 400)

    image = parking_dialog.preview.grab()

    assert not image.isNull()
    assert parking_dialog.preview.network is not None
