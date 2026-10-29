import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest

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


def click(widget, point, button=Qt.LeftButton):
    QTest.mouseClick(widget, button, Qt.NoModifier, point.toPoint())


def sized(parking_dialog):
    parking_dialog.preview.resize(480, 400)
    parking_dialog.side_view.resize(600, 150)
    parking_dialog._update()
    return parking_dialog


def test_single_gaps_are_kept_when_the_number_of_bays_changes(qapp):
    parking_dialog = dialog()
    parking_dialog.gaps[1] = 0.8
    parking_dialog._update()

    assert parking_dialog.gap_input.text() == " "

    parking_dialog.bays_input.setValue(3)
    assert parking_dialog.settings.gaps == (0.0, 0.8)

    parking_dialog.gap_input.setValue(0.3)
    assert parking_dialog.settings.gaps == (0.3, 0.3)


def test_clicking_a_side_label_opens_that_side(qapp):
    parking_dialog = sized(dialog())

    click(parking_dialog.preview, parking_dialog.preview.side_labels()["left"].center())

    assert parking_dialog.settings.open_side == "left"


def test_clicking_a_wall_edits_its_offset_in_a_popup(qapp):
    parking_dialog = sized(dialog())
    areas = dict(parking_dialog.preview.length_areas())

    click(parking_dialog.preview, areas["left"].center())
    popup = parking_dialog.popup
    assert popup.value() == 0.5

    popup.setValue(1.2)
    QTest.keyClick(popup, Qt.Key_Return)
    assert parking_dialog.left_input.value() == 1.2

    click(parking_dialog.preview, areas["back"].center())
    parking_dialog.popup.setValue(3.0)
    QTest.keyClick(parking_dialog.popup, Qt.Key_Escape)
    assert parking_dialog.back_input.value() == 2.0


def test_clicking_a_gap_edits_only_that_gap(qapp):
    parking_dialog = sized(dialog())

    click(parking_dialog.preview, dict(parking_dialog.preview.length_areas())[1].center())
    parking_dialog.popup.setValue(0.6)
    QTest.keyClick(parking_dialog.popup, Qt.Key_Return)

    assert parking_dialog.settings.gaps == (0.0, 0.6, 0.0)


def test_side_view_splits_segments_and_deletes_nodes(qapp):
    parking_dialog = sized(dialog())
    side_view = parking_dialog.side_view
    before = parking_dialog.settings.bay_line or side_view.line

    click(side_view, side_view.plus_points()[0])
    line = parking_dialog.bay_line
    assert line.segments[:2] == (0.25, 0.25)

    click(side_view, side_view.node_points()[1])
    assert side_view.selected == 1
    QTest.keyClick(side_view, Qt.Key_Delete)
    assert parking_dialog.bay_line == before

    # The marker can't be deleted.
    click(side_view, side_view.node_points()[0])
    QTest.keyClick(side_view, Qt.Key_Delete)
    assert parking_dialog.bay_line == before


def test_side_view_segments_and_turn_are_edited_in_a_popup(qapp):
    parking_dialog = sized(dialog())
    side_view = parking_dialog.side_view
    nodes = side_view.node_points()

    click(side_view, (nodes[2] + nodes[3]) / 2)
    parking_dialog.popup.setValue(2.0)
    QTest.keyClick(parking_dialog.popup, Qt.Key_Return)
    assert parking_dialog.bay_line.segments[2] == 2.0

    turn = side_view.turn_points()
    click(side_view, (turn[0] + turn[1]) / 2)
    parking_dialog.popup.setValue(2.5)
    QTest.keyClick(parking_dialog.popup, Qt.Key_Return)
    assert parking_dialog.bay_line.turn[1] == 2.5

    parking_dialog.reset_shed_settings()
    assert parking_dialog.bay_line is None


def test_branches_are_dragged_to_a_node(qapp):
    parking_dialog = sized(dialog())
    side_view = parking_dialog.side_view
    line = side_view.line
    nodes = side_view.node_points()

    QTest.mousePress(side_view, Qt.LeftButton, Qt.NoModifier, side_view.exit_point().toPoint())
    QTest.mouseMove(side_view, nodes[-1].toPoint())
    QTest.mouseRelease(side_view, Qt.LeftButton, Qt.NoModifier, nodes[-1].toPoint())

    assert parking_dialog.bay_line.exit_node == len(line.segments)
    assert parking_dialog.bay_line.entry_node == line.entry_node


def test_dragging_the_entry_branch_moves_the_entry_line(qapp):
    parking_dialog = sized(dialog())
    side_view = parking_dialog.side_view
    line = side_view.line
    # Where the square ends up: 1.3 m inside the node two further out.
    node = side_view.node_points()[line.entry_node + 2]
    shed_x = side_view.node_points()[0].x()
    target = QPoint(
        round(node.x() - 1.3 * (node.x() - shed_x) / line.distances[line.entry_node + 2]),
        round(side_view.entry_point().y()),
    )

    QTest.mousePress(side_view, Qt.LeftButton, Qt.NoModifier, side_view.entry_point().toPoint())
    QTest.mouseMove(side_view, target)
    QTest.mouseRelease(side_view, Qt.LeftButton, Qt.NoModifier, target)

    assert parking_dialog.bay_line.entry_node == line.entry_node + 2
    # G1's nodes 2.3, 3.3 and 4.8 m outside: the entry line moves from 1.0 to 3.5 m outside.
    network = parking_dialog.preview.network
    assert any(abs(d + 3.5) < 1e-6 for _, d in network.points)
    assert side_view.entry_point().x() == pytest.approx(target.x(), abs=2)


def test_entry_branch_inside_the_shed_disables_create(qapp):
    parking_dialog = dialog()
    parking_dialog.back_input.setValue(12.0)
    parking_dialog._set_bay_line(parking_dialog.side_view.line)

    # The edited line keeps its lengths, so its entry node moves into the shed with the marker.
    parking_dialog.back_input.setValue(0.5)

    assert not parking_dialog.is_valid
    assert parking_dialog.hint_label.text() == (
        "The entry line must be at least 1.0 m outside the shed."
    )


def test_drive_through_side_view_is_read_only(qapp):
    parking_dialog = sized(dialog())
    parking_dialog.mode_input.setCurrentIndex(1)
    side_view = parking_dialog.side_view

    assert side_view.line is None
    click(side_view, side_view.node_points()[3])
    assert side_view.selected is None
    assert not side_view.grab().isNull()
