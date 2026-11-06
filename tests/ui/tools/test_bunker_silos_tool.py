"""Picking bunker silos for their lanes."""

import pytest
from mouse_helpers import click, drag, view_pos
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

from autodrive_editor.file_io.savegame_buildings import (
    BuildingGroup,
    BuildingType,
    SavegameBuildings,
)
from autodrive_editor.file_io.savegame_sheds import IndoorArea
from autodrive_editor.ui.dialogs.parking_map_overlay import ParkingMapOverlay
from autodrive_editor.ui.tools.generate_tool import GenerateTask

# Two silos side by side below the nodes 1–3 on the line z=0.
LEFT = IndoorArea("silo.xml", "1", ((0, 5), (9, 5), (9, 25), (0, 25)), 0.0, "Farm")
RIGHT = IndoorArea("silo.xml", "2", ((10, 5), (19, 5), (19, 25), (10, 25)), 0.0, "Farm")


@pytest.fixture
def silo_window(zoomed_window):
    window = zoomed_window
    window.asked = []

    def ask(areas, autodrive_data):
        window.asked.append(areas)
        return None

    window.generators.ask_silo_settings = ask
    silo_type = BuildingType("silo.xml", "Silo", "silos", BuildingGroup.BUNKER_SILOS, 1)
    window.scene_renderer.set_buildings(SavegameBuildings(types=[silo_type], silos=[LEFT, RIGHT]))
    window.set_generate_task(GenerateTask.BUNKER_SILOS)
    return window


def picked(window):
    return len(window.scene_renderer.silo_layer.picked)


def test_click_on_a_silo_opens_it(silo_window):
    click(silo_window, view_pos(silo_window, 5, 15))

    assert silo_window.asked == [[LEFT]]
    assert picked(silo_window) == 0


def test_shift_clicks_collect_silos_and_enter_opens_them(silo_window):
    click(silo_window, view_pos(silo_window, 15, 15), modifiers=Qt.ShiftModifier)
    click(silo_window, view_pos(silo_window, 5, 15), modifiers=Qt.ShiftModifier)

    assert silo_window.asked == []
    assert picked(silo_window) == 2

    QTest.keyClick(silo_window.view, Qt.Key_Return)

    assert silo_window.asked == [[RIGHT, LEFT]]
    assert picked(silo_window) == 0


def test_shift_click_on_a_picked_silo_removes_it_and_esc_drops_the_pick(silo_window):
    click(silo_window, view_pos(silo_window, 5, 15), modifiers=Qt.ShiftModifier)
    click(silo_window, view_pos(silo_window, 15, 15), modifiers=Qt.ShiftModifier)
    click(silo_window, view_pos(silo_window, 5, 15), modifiers=Qt.ShiftModifier)

    assert picked(silo_window) == 1

    QTest.keyClick(silo_window.view, Qt.Key_Escape)
    QTest.keyClick(silo_window.view, Qt.Key_Return)

    assert picked(silo_window) == 0
    assert silo_window.asked == []


def test_click_on_a_picked_silo_opens_the_pick(silo_window):
    click(silo_window, view_pos(silo_window, 5, 15), modifiers=Qt.ShiftModifier)
    click(silo_window, view_pos(silo_window, 15, 15), modifiers=Qt.ShiftModifier)
    click(silo_window, view_pos(silo_window, 15, 15))

    assert silo_window.asked == [[LEFT, RIGHT]]


def test_right_drag_opens_the_silos_in_the_box(silo_window):
    drag(
        silo_window,
        view_pos(silo_window, -2, 3),
        view_pos(silo_window, 21, 27),
        button=Qt.RightButton,
    )

    assert silo_window.asked == [[LEFT, RIGHT]]


def test_dialog_shows_the_lanes_of_all_silos_on_the_map(zoomed_window, monkeypatch):
    window = zoomed_window
    seen = {}

    def run(dialog):
        overlays = [item for item in window.scene.items() if isinstance(item, ParkingMapOverlay)]
        seen["markers"] = len(overlays[0].network.markers)
        return True

    monkeypatch.setattr(window.generators, "_run_beside_map", run)

    settings = window.generators.ask_silo_settings(
        [LEFT, RIGHT], window.project_coordinator.autodrive_data
    )

    # 9 m wide: 2 lanes each.
    assert seen["markers"] == 4
    assert settings.silo
    assert not any(isinstance(item, ParkingMapOverlay) for item in window.scene.items())
