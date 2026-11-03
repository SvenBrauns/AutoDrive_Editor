import pytest
from PySide6.QtCore import Qt

from autodrive_editor.editing.station_layout import MarkerRule, StationSettings
from autodrive_editor.file_io.savegame_stations import Stop, StopKind
from autodrive_editor.model.autodrive_data import NodeData
from autodrive_editor.settings.app_settings import AppSettings
from autodrive_editor.ui.dialogs.generator_settings_widget import GeneratorSettingsDialog
from autodrive_editor.ui.dialogs.station_dialog import GROUP, NAME, NOTE, STOP, StationDialog

pytestmark = pytest.mark.usefixtures("isolated_user_data")

SELL = Stop("store.xml", "1", "Store ", StopKind.SELL, ("WHEAT",), (0, 0, 0), 90.0, True)
BUY = Stop("store.xml", "1", "Store ", StopKind.BUY, ("SEEDS",), (0, 0, 30), 90.0, False)


def dialog(taken=(), nodes=(), headings=(90, 270)):
    return StationDialog([SELL, BUY], list(headings), set(taken), list(nodes), AppSettings())


def test_all_stops_are_chosen_with_default_markers_and_headings(qapp):
    choices = dialog().choices

    assert [(c.stop, c.name, c.group, c.heading) for c in choices] == [
        (SELL, "Store (Selling point)", "Selling points", 90),
        (BUY, "Store (Buying station)", "Buying stations", 270),
    ]


def test_taken_marker_names_get_a_number(qapp):
    choices = dialog(taken={("Store (Selling point)", "Selling points")}).choices

    assert choices[0].name == "Store (Selling point) 2"


def test_unchecked_stops_are_left_out_and_angles_are_passed_on(qapp):
    station_dialog = dialog()
    station_dialog.table.item(0, STOP).setCheckState(Qt.Unchecked)
    station_dialog.set_heading(1, 361.4)

    assert [(c.stop, c.heading) for c in station_dialog.choices] == [(BUY, 1)]


def test_notes_name_a_missing_ai_node_and_an_existing_node_on_the_lane(qapp):
    station_dialog = dialog(nodes=[NodeData(1, 8, 0, 0)])

    assert station_dialog.table.item(0, NOTE).text() == "existing node on the lane"
    assert station_dialog.table.item(1, NOTE).toolTip() == "no AI node"


def test_handles_sit_at_the_front_end_of_the_chosen_lanes(qapp):
    AppSettings().set_station_settings(StationSettings(after=2, marker=0))
    station_dialog = dialog()

    (sell, buy) = station_dialog.handles()
    # At least 5 m from the stop, so short lanes can still be grabbed.
    assert sell == pytest.approx((0, 5, 0, 0, 0))
    assert buy == pytest.approx((1, -5, 30, 0, 30))

    # The lane goes on past the marker.
    AppSettings().set_station_settings(StationSettings(after=2, marker=8))
    station_dialog.reload_settings()
    assert station_dialog.handles()[0] == pytest.approx((0, 10, 0, 0, 0))

    station_dialog.table.item(0, STOP).setCheckState(Qt.Unchecked)
    assert [handle[0] for handle in station_dialog.handles()] == [1]


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


def test_preview_follows_the_choices_and_settings(qapp):
    AppSettings().set_station_settings(StationSettings(5, 5, marker=0))
    AppSettings().set_generator_spacing(5)
    station_dialog = dialog()
    plans = []
    station_dialog.plan_changed.connect(lambda network, points: plans.append((network, points)))
    station_dialog.reload_settings()

    network, points = plans[-1]
    assert len(points) == 6
    assert [index for index, *_ in network.markers] == [1, 4]

    station_dialog.set_heading(0, 180)
    assert plans[-1][1][0] == pytest.approx((0, -5))


def test_settings_button_renames_only_unedited_markers(qapp, monkeypatch):
    station_dialog = dialog()
    station_dialog.table.item(1, NAME).setText("Seeds")

    def change_settings(settings_dialog):
        rules = settings_dialog.page.rules | {StopKind.SELL: MarkerRule("VK-{building}", "VK")}
        AppSettings().set_marker_rules(rules)
        return True

    monkeypatch.setattr(GeneratorSettingsDialog, "exec", change_settings)
    station_dialog.settings_button.click()

    assert [(c.name, c.group) for c in station_dialog.choices] == [
        ("VK-Store", "VK"),
        ("Seeds", "Buying stations"),
    ]
