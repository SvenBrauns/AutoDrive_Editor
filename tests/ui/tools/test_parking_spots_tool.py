"""Creating parking spots by clicking a shed."""

import pytest
from mouse_helpers import click, hover, view_pos
from PySide6.QtCore import QEvent, QTimer
from PySide6.QtWidgets import QApplication, QDialog, QLabel

from autodrive_editor.editing.parking_layout import ParkingSettings
from autodrive_editor.file_io.savegame_buildings import (
    BuildingGroup,
    BuildingType,
    SavegameBuildings,
)
from autodrive_editor.file_io.savegame_sheds import IndoorArea
from autodrive_editor.ui.dialogs.parking_map_overlay import ParkingMapOverlay
from autodrive_editor.ui.tools.interaction_mode import InteractionMode
from autodrive_editor.ui.tools.navigate_tool import NavigateTool

# Below the nodes 1–3 on the line z=0.
SHED = IndoorArea(
    "shed.xml", "1", ((0, 10), (20, 10), (20, 20), (0, 20)), 5.0, "Farm barn", "sheds"
)


@pytest.fixture
def parking_window(zoomed_window):
    window = zoomed_window
    window.asked = []

    def ask(area, autodrive_data):
        window.asked.append(area)
        return ParkingSettings(bays=2, gaps=(0.0,), marker_name="Shed", group="Farm")

    window._ask_parking_settings = ask
    shed_type = BuildingType("shed.xml", "Farm barn", "sheds", BuildingGroup.SHEDS, 1)
    window.scene_renderer.set_buildings(SavegameBuildings(types=[shed_type], areas=[SHED]))
    window.set_interaction_mode(InteractionMode.PARKING_SPOTS)
    return window


def test_click_on_a_shed_creates_its_parking_spots(parking_window):
    data = parking_window.project_coordinator.autodrive_data

    click(parking_window, view_pos(parking_window, 10, 15))

    assert parking_window.asked == [SHED]
    assert [marker.name for marker in data.markers.values()] == ["Shed 1", "Shed 2"]
    assert len(parking_window.node_selection.selected_node_ids) == 4
    assert parking_window.status.text().startswith("2 parking spots created")

    parking_window.edit_history.undo()

    assert list(data.nodes) == [1, 2, 3]


def test_click_beside_the_shed_does_not_ask(parking_window):
    click(parking_window, view_pos(parking_window, 10, 30))

    assert parking_window.asked == []


def test_tool_sits_next_to_the_selection(parking_window):
    actions = parking_window.actions
    toolbar = actions.quick_access_toolbar.actions()

    assert toolbar.index(actions.parking_action) == toolbar.index(actions.selection_action) + 1


def hover_label(window):
    label = window.view.viewport().findChild(QLabel)
    return label if label is not None and label.isVisible() else None


def test_hovering_a_shed_shows_its_name_beside_the_pointer(parking_window):
    hover(parking_window, view_pos(parking_window, 10, 15))

    label = hover_label(parking_window)
    assert label.text() == "Farm barn – Vehicle sheds"
    first = label.pos()

    # The name follows the pointer on the shed.
    hover(parking_window, view_pos(parking_window, 12, 15))

    assert hover_label(parking_window).pos() != first

    hover(parking_window, view_pos(parking_window, 10, 30))

    assert hover_label(parking_window) is None


def test_hover_name_is_hidden_when_the_pointer_leaves_the_map(parking_window):
    hover(parking_window, view_pos(parking_window, 10, 15))

    QApplication.sendEvent(parking_window.view, QEvent(QEvent.Leave))

    assert hover_label(parking_window) is None


def test_hover_name_is_hidden_when_the_tool_changes(parking_window):
    hover(parking_window, view_pos(parking_window, 10, 15))

    parking_window.set_interaction_mode(InteractionMode.SELECT)

    assert hover_label(parking_window) is None


def test_dialog_shows_its_plan_on_the_map_and_keeps_the_map_movable(zoomed_window, monkeypatch):
    window = zoomed_window
    data = window.project_coordinator.autodrive_data
    seen = {}

    def run(dialog):
        overlays = [item for item in window.scene.items() if isinstance(item, ParkingMapOverlay)]
        seen["markers"] = len(overlays[0].network.markers)
        dialog.bays_input.setValue(1)
        seen["after_change"] = len(overlays[0].network.markers)
        dialog.group_input.setCurrentText("Farm")
        return True

    monkeypatch.setattr(window, "_run_beside_map", run)

    settings = window._ask_parking_settings(SHED, data)

    assert seen["markers"] > 1 and seen["after_change"] == 1
    assert settings.bays == 1
    assert not any(isinstance(item, ParkingMapOverlay) for item in window.scene.items())


def test_only_the_map_can_be_used_while_the_dialog_is_open(zoomed_window):
    window = zoomed_window
    dialog = QDialog(window)
    before = window.view.active_tool
    seen = {}

    def check():
        seen["tool"] = window.view.active_tool
        seen["visible"] = dialog.isVisible()
        dialog.accept()

    QTimer.singleShot(0, check)

    assert window._run_beside_map(dialog)
    assert isinstance(seen["tool"], NavigateTool) and seen["tool"] is not before
    assert seen["visible"]
    assert window.view.active_tool is before
