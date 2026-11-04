import pytest

from autodrive_editor.editing.parking_layout import ParkingMode
from autodrive_editor.file_io.savegame_sheds import IndoorArea
from autodrive_editor.settings.app_settings import AppSettings
from autodrive_editor.ui.dialogs.silo_dialog import SiloDialog

pytestmark = pytest.mark.usefixtures("isolated_user_data")

# Two farm silos side by side, 28 × 21 m (5 lanes), open towards +z; no map: back in.
LEFT = IndoorArea("silo.xml", "1", ((0, 0), (28, 0), (28, 21), (0, 21)), 80.0, "Farm")
RIGHT = IndoorArea("silo.xml", "2", ((29, 0), (57, 0), (57, 21), (29, 21)), 80.0, "Farm")


def dialog(areas=(LEFT, RIGHT), taken=()):
    return SiloDialog(list(areas), None, ["Farm-KS-A"], set(taken), AppSettings())


def test_defaults_are_the_silo_layout_and_patterns(qapp):
    silo_dialog = dialog()
    settings = silo_dialog.settings

    assert settings.silo and settings.mode == ParkingMode.BACK_IN
    assert settings.bays == 5
    assert (settings.marker_name, settings.group) == ("KS-{letter}-{n}", "{building}-KS-{letter}")
    assert silo_dialog.is_valid
    assert silo_dialog.hint_label.text().splitlines() == [
        "Farm-KS-A: KS-A-1 … KS-A-5",
        "Farm-KS-B (new): KS-B-1 … KS-B-5",
    ]
    assert len(silo_dialog.area_plan.markers) == 10


def test_silo_choice_switches_the_preview_and_is_hidden_for_one_silo(qapp):
    silo_dialog = dialog()

    assert silo_dialog.area_input.count() == 2
    silo_dialog.area_input.setCurrentIndex(1)
    assert silo_dialog.preview.area == silo_dialog.area_input.itemData(1)

    assert not dialog([LEFT]).form.isRowVisible(dialog([LEFT]).area_input)


def test_drive_through_swaps_patterns_and_marker_distance(qapp):
    silo_dialog = dialog()
    silo_dialog.mode_input.setCurrentIndex(
        silo_dialog.mode_input.findData(ParkingMode.DRIVE_THROUGH)
    )
    settings = silo_dialog.settings

    assert settings.marker_name == "DS-{letter}-{n}"
    assert settings.back_offset == -15.0
    assert silo_dialog.back_input.value() == 15.0


@pytest.mark.parametrize(
    "name, taken",
    [("KS-{letter}", ()), ("KS-{x}-{n}", ()), ("KS-{letter}-{n}", {("KS-B-2", "Farm-KS-B")})],
)
def test_bad_or_taken_names_disable_create(qapp, name, taken):
    silo_dialog = dialog(taken=taken)
    silo_dialog.name_input.setText(name)

    assert not silo_dialog.is_valid
    assert silo_dialog.area_plan is None
