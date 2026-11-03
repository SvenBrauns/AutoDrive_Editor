import pytest
from PySide6.QtCore import Qt

from autodrive_editor.editing.station_layout import (
    LaneEnd,
    MarkerRule,
    StationSettings,
    plan_stations,
)
from autodrive_editor.file_io.savegame_stations import Stop, StopKind
from autodrive_editor.model.autodrive_data import AutoDriveData, NodeData
from autodrive_editor.settings.app_settings import AppSettings
from autodrive_editor.ui.dialogs.generator_settings_widget import GeneratorSettingsDialog
from autodrive_editor.ui.dialogs.station_dialog import (
    GROUP,
    NAME,
    NOTE,
    STOP,
    LaneHandle,
    StationDialog,
)

pytestmark = pytest.mark.usefixtures("isolated_user_data")

SELL = Stop("store.xml", "1", "Store ", StopKind.SELL, ("WHEAT",), (0, 0, 0), 90.0, True)
BUY = Stop("store.xml", "1", "Store ", StopKind.BUY, ("SEEDS",), (0, 0, 30), 90.0, False)


def dialog(taken=(), nodes=(), headings=(90, 270)):
    data = AutoDriveData()

    for node in nodes:
        data.add_node(node)

    return StationDialog([SELL, BUY], list(headings), set(taken), data, AppSettings())


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


def test_handles_sit_at_the_lane_ends_and_the_marker(qapp):
    AppSettings().set_station_settings(StationSettings(before=10, after=2, marker=0))
    station_dialog = dialog()

    handles = station_dialog.handles()
    # The turn handle at least 5 m from the stop, so short lanes can still be turned.
    assert handles[:3] == [
        (0, LaneHandle.START, pytest.approx(-10), pytest.approx(0)),
        (0, LaneHandle.END, pytest.approx(2), pytest.approx(0)),
        (0, LaneHandle.TURN, pytest.approx(5), pytest.approx(0)),
    ]
    assert handles[5][2:] == pytest.approx((-5, 30))

    AppSettings().set_station_settings(StationSettings(before=10, after=2, marker=8))
    station_dialog.reload_settings()
    assert station_dialog.handles()[2][2:] == pytest.approx((8, 0))

    station_dialog.table.item(0, STOP).setCheckState(Qt.Unchecked)
    assert {handle[0] for handle in station_dialog.handles()} == {1}


def test_lane_ends_bend_join_a_fitting_node_and_straighten_when_turned(qapp):
    road = NodeData(1, 20, 0, 10, outgoing={2})
    station_dialog = dialog(nodes=[road, NodeData(2, 30, 0, 10), NodeData(3, 20, 0, -10)])
    start, end, turn = station_dialog.handles()[:3]

    station_dialog.drag_handle(end, 21, 11, node_id=1)
    # Node 3 is not driven to, so the lane cannot start there.
    station_dialog.drag_handle(start, 19, -9, node_id=3)

    choice = station_dialog.choices[0]
    assert (choice.start, choice.end) == (LaneEnd(19, -9), LaneEnd(20, 10, 1))
    assert "existing node" not in station_dialog.table.item(0, NOTE).text()

    station_dialog.drag_handle(turn, 1, 10, snap=True)

    choice = station_dialog.choices[0]
    assert (choice.heading, choice.start, choice.end) == (180, None, None)


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


def test_legs_to_a_nearby_road_are_previewed(qapp):
    data = AutoDriveData()
    data.add_node(NodeData(1, -100, 0, -20))
    data.add_node(NodeData(2, 100, 0, -20))
    data.nodes[1].outgoing.add(2)
    data.nodes[2].incoming.add(1)
    station_dialog = StationDialog([SELL], [90], set(), data, AppSettings())
    shown = []
    station_dialog.plan_changed.connect(lambda piece, points: shown.append(piece))
    lane_count = len(plan_stations(station_dialog.choices, station_dialog.settings).points)

    station_dialog.update_legs()

    assert len(shown[-1].points) > lane_count
    assert station_dialog.table.item(0, NOTE).text() == ""


def test_a_stop_without_a_road_is_noted(qapp):
    station_dialog = dialog()

    station_dialog.update_legs()

    assert "50" in station_dialog.table.item(0, NOTE).text()
