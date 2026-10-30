import pytest
from PySide6.QtCore import Qt

from autodrive_editor.editing.station_layout import StationSettings
from autodrive_editor.file_io.savegame_stations import Stop, StopKind
from autodrive_editor.model.autodrive_data import NodeData
from autodrive_editor.settings.app_settings import AppSettings
from autodrive_editor.ui.dialogs.station_dialog import GROUP, NAME, NOTE, STOP, TURN, StationDialog

pytestmark = pytest.mark.usefixtures("isolated_user_data")

SELL = Stop("store.xml", "1", "Store ", StopKind.SELL, ("WHEAT",), (0, 0, 0), 90.0, True)
BUY = Stop("store.xml", "1", "Store ", StopKind.BUY, ("SEEDS",), (0, 0, 30), 90.0, False)


def dialog(taken=(), nodes=()):
    return StationDialog([SELL, BUY], set(taken), list(nodes), AppSettings())


def test_all_stops_are_chosen_with_default_markers(qapp):
    choices = dialog().choices

    assert [(c.stop, c.name, c.group, c.turned) for c in choices] == [
        (SELL, "Store (Selling point)", "Selling points", False),
        (BUY, "Store (Buying station)", "Buying stations", False),
    ]


def test_taken_marker_names_get_a_number(qapp):
    choices = dialog(taken={("Store (Selling point)", "Selling points")}).choices

    assert choices[0].name == "Store (Selling point) 2"


def test_unchecked_stops_are_left_out_and_turn_is_passed_on(qapp):
    station_dialog = dialog()
    station_dialog.table.item(0, STOP).setCheckState(Qt.Unchecked)
    station_dialog.table.item(1, TURN).setCheckState(Qt.Checked)

    assert [(c.stop, c.turned) for c in station_dialog.choices] == [(BUY, True)]


def test_notes_name_a_missing_ai_node_and_an_existing_node_on_the_lane(qapp):
    station_dialog = dialog(nodes=[NodeData(1, 5, 0, 0)])

    assert station_dialog.table.item(0, NOTE).text() == "existing node on the lane"
    assert station_dialog.table.item(1, NOTE).text() == "no AI node, direction from the building"


def test_duplicate_or_empty_names_and_no_choice_block_create(qapp):
    station_dialog = dialog()
    assert station_dialog.is_valid

    station_dialog.table.item(1, NAME).setText("Store (Selling point)")
    assert station_dialog.is_valid

    station_dialog.table.item(1, GROUP).setText("Selling points")
    assert not station_dialog.is_valid

    station_dialog.table.item(1, NAME).setText("")
    assert not station_dialog.is_valid

    station_dialog.table.item(1, NAME).setText("Other")
    assert station_dialog.is_valid

    for row in range(2):
        station_dialog.table.item(row, STOP).setCheckState(Qt.Unchecked)
    assert not station_dialog.is_valid


def test_preview_follows_the_choices_and_settings_are_kept(qapp):
    station_dialog = dialog()
    plans = []
    station_dialog.plan_changed.connect(lambda network, points: plans.append((network, points)))

    station_dialog.before_input.setValue(5)
    station_dialog.after_input.setValue(5)
    station_dialog.spacing_input.setValue(5)

    network, points = plans[-1]
    assert len(points) == 6
    assert [index for index, _ in network.markers] == [1, 4]

    station_dialog.accept()

    assert AppSettings().station_settings == StationSettings(5, 5, 5)
