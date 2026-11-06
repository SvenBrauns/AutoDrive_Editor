"""Generate → Roads with the real window."""

from pathlib import Path

from PySide6.QtWidgets import QApplication
from road_lane_helpers import junction

from autodrive_editor.ui.tools.generate_tool import GenerateTask

LANES = junction([0, 90, 180], centre=(500, 500))


def choose_roads(window):
    operation = window.road_network_operation
    operation.savegame_provider = lambda: Path("savegame")
    operation.read_lanes = lambda savegame: LANES
    operation.run = lambda title, work: work(lambda *progress: None, lambda: False)
    window.set_generate_task(GenerateTask.ROADS)
    # The lanes are read after the tool change.
    QApplication.processEvents()


def test_the_lanes_are_shown_while_roads_is_chosen(zoomed_window):
    choose_roads(zoomed_window)

    assert zoomed_window.scene_renderer.traffic_lanes == LANES

    zoomed_window.set_generate_task(GenerateTask.ROUTE)

    assert zoomed_window.scene_renderer.traffic_lanes == []


def test_create_builds_the_whole_map_into_the_plan(zoomed_window):
    choose_roads(zoomed_window)
    before = len(zoomed_window._get_autodrive_data().nodes)
    found = []
    zoomed_window.road_network_operation.places_found.connect(found.append)

    zoomed_window.generate_options.create_roads_button.click()

    assert len(zoomed_window._get_autodrive_data().nodes) > before
    assert zoomed_window.planning.changes is not None
    assert zoomed_window.check_dock.road_places == found[0]
