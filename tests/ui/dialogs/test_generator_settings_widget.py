import pytest

from autodrive_editor.editing.parking.parking_layout import ParkingMode
from autodrive_editor.editing.stations.station_layout import MarkerRule, StationSettings
from autodrive_editor.file_io.savegame_stations import StopKind
from autodrive_editor.settings.app_settings import AppSettings
from autodrive_editor.ui.dialogs.generator_settings_widget import GeneratorSettingsDialog

pytestmark = pytest.mark.usefixtures("isolated_user_data")


def test_ok_stores_spacing_station_lanes_and_marker_rules(qapp):
    dialog = GeneratorSettingsDialog(AppSettings())
    page = dialog.page
    row = list(StopKind).index(StopKind.PRODUCTION)

    page.spacing_input.setValue(8)
    page.before_input.setValue(6)
    page.marker_input.setValue(3)
    page.after_input.setValue(4)
    page.rules_table.item(row, 1).setText("VK-{building}")
    page.rules_table.item(row, 2).setText("VK")
    page.start_input.setValue(5)
    dialog.accept()

    settings = AppSettings()
    assert settings.station_settings == StationSettings(6, 4, 8, 3)
    assert settings.marker_rules[StopKind.PRODUCTION] == MarkerRule("VK-{building}", "VK")
    assert settings.marker_start == 5


def test_an_empty_group_disables_ok(qapp):
    dialog = GeneratorSettingsDialog(AppSettings())

    dialog.page.rules_table.item(0, 2).setText(" ")

    assert not dialog.ok_button.isEnabled()
    assert dialog.page.problem_label.text()

    dialog.page.rules_table.item(0, 2).setText("Shops")

    assert dialog.ok_button.isEnabled()


def test_silo_patterns_are_stored_and_bad_ones_disable_ok(qapp):
    dialog = GeneratorSettingsDialog(AppSettings())
    table = dialog.page.silo_table

    table.item(1, 1).setText("{letter}-{x}")

    assert not dialog.ok_button.isEnabled()

    table.item(1, 1).setText("{letter}{n}")
    dialog.accept()

    assert AppSettings().silo_patterns[ParkingMode.DRIVE_THROUGH] == (
        "{letter}{n}",
        "{building}-DS-{letter}",
    )
