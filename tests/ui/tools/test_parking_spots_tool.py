"""Creating parking spots by clicking a shed."""

import pytest
from mouse_helpers import click, view_pos

from autodrive_editor.editing.parking_layout import ParkingSettings
from autodrive_editor.file_io.savegame_sheds import IndoorArea
from autodrive_editor.ui.tools.interaction_mode import InteractionMode

# Below the nodes 1–3 on the line z=0.
SHED = IndoorArea("shed.xml", "1", ((0, 10), (20, 10), (20, 20), (0, 20)), 5.0)


@pytest.fixture
def parking_window(zoomed_window):
    window = zoomed_window
    window.asked = []

    def ask(area, autodrive_data):
        window.asked.append(area)
        return ParkingSettings(bays=2, gaps=(0.0,), marker_name="Shed", group="Farm")

    window._ask_parking_settings = ask
    window.scene_renderer.set_shed_areas([SHED])
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
