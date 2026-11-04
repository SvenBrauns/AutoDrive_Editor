"""Creating station lanes by picking station buildings."""

import pytest
from mouse_helpers import click, drag, hover, view_pos
from PySide6.QtCore import QEvent, Qt, QTimer
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QApplication

from autodrive_editor.editing.station_layout import StationSettings, StopChoice
from autodrive_editor.file_io.savegame_buildings import (
    BuildingGroup,
    BuildingType,
    SavegameBuildings,
)
from autodrive_editor.file_io.savegame_stations import Stop, StopKind
from autodrive_editor.ui.dialogs.station_dialog import StationDialog
from autodrive_editor.ui.tools.generate_tool import GenerateTask

# Two stops of one store and one of a barn, below the nodes 1–3 on the line z=0.
STORE_A = Stop("store.xml", "1", "Store", StopKind.SELL, ("WHEAT",), (0, 0, 15), 90.0, True)
STORE_B = Stop("store.xml", "1", "Store", StopKind.BUY, ("SEEDS",), (10, 0, 15), 90.0, True)
BARN = Stop("barn.xml", "2", "Barn", StopKind.ANIMALS, ("WATER",), (40, 0, 25), 0.0, False)


@pytest.fixture
def station_window(zoomed_window):
    window = zoomed_window
    window.asked = []

    def ask(stops, autodrive_data):
        window.asked.append(stops)
        return [StopChoice(stop, stop.name, "Stations", 90) for stop in stops[:1]], StationSettings(
            5, 5, 5
        )

    window._ask_station_choices = ask
    types = [
        BuildingType("store.xml", "Store", "stations", BuildingGroup.STATIONS, 1),
        BuildingType("barn.xml", "Barn", "stations", BuildingGroup.STATIONS, 1),
    ]
    buildings = SavegameBuildings(types=types, stops=[STORE_A, STORE_B, BARN])
    window.scene_renderer.set_buildings(buildings)
    window.set_generate_task(GenerateTask.STATIONS)
    return window


def test_click_on_a_stop_picks_all_stops_of_its_building(station_window):
    data = station_window.project_coordinator.autodrive_data

    click(station_window, view_pos(station_window, 10, 15))

    assert station_window.asked == [[STORE_A, STORE_B]]
    assert station_window.edit_history.is_planning
    assert [marker.name for marker in data.markers.values()] == ["Store"]
    assert station_window.status.text().startswith("1 station lanes created")

    station_window.edit_history.undo()

    assert list(data.nodes) == [1, 2, 3]


def test_click_between_the_stops_of_a_building_picks_it(station_window):
    click(station_window, view_pos(station_window, 5, 15))

    assert station_window.asked == [[STORE_A, STORE_B]]


def test_click_away_from_stations_does_not_ask(station_window):
    click(station_window, view_pos(station_window, 10, 40))

    assert station_window.asked == []


def test_right_drag_picks_the_stops_in_the_box(station_window):
    drag(
        station_window,
        view_pos(station_window, 8, 10),
        view_pos(station_window, 45, 30),
        button=Qt.RightButton,
    )

    assert station_window.asked == [[STORE_B, BARN]]


def test_hovering_a_station_shows_its_name(station_window):
    hover(station_window, view_pos(station_window, 40, 25))

    labels = [w for w in station_window.view.viewport().children() if hasattr(w, "text")]
    assert any(label.isVisible() and label.text() == "Barn" for label in labels)


def test_yard_road_is_drawn_by_clicks_on_the_map_and_finished_with_enter(zoomed_window):
    window = zoomed_window
    data = window.project_coordinator.autodrive_data
    seen = {}

    def draw():
        dialog = window.findChild(StationDialog)
        dialog.draw_button.click()
        click(window, view_pos(window, -80, 30))
        click(window, view_pos(window, 120, 30))
        enter = QKeyEvent(QEvent.KeyPress, Qt.Key_Return, Qt.NoModifier)
        QApplication.sendEvent(window.view, enter)
        seen["drawing"] = dialog.drawing
        dialog.accept()

    QTimer.singleShot(0, draw)
    lanes, _, yard = window._ask_station_choices([STORE_A, STORE_B], data)

    assert seen["drawing"] is False
    assert lanes == [] and len(yard[0].piece.markers) == 2
