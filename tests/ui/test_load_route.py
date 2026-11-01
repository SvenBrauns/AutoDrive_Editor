"""File → Load route into savegame…"""

import pytest
from game_folder_helpers import add_routes, add_savegame, make_game_folder
from PySide6.QtWidgets import QMessageBox

from autodrive_editor.file_io.autodrive_xml import AutoDriveXmlReader

MAP_NAME = "LS25_X"


@pytest.fixture
def load_window(window, tmp_path):
    """Savegame 1 (2 nodes) is open; the RoutesManager has route "Hof" (3 nodes) of its map."""

    folder = make_game_folder(tmp_path / "FarmingSimulator2025")
    window.settings.set_game_folder(folder)
    add_routes(folder, [("Hof", "abc.xml", MAP_NAME, 2), ("Fremd", "def.xml", "Other", 1)])
    window.savegame = add_savegame(folder, 1, "Spielstand", "LS25 X", MAP_NAME)
    window.project_coordinator.load_xml_file(window.savegame / "AutoDrive_config.xml")
    window.answers = []
    window.offered = []
    window.files._ask_save_network_first = lambda: window.answers.pop(0)
    window.files._choose_route = lambda routes: window.offered.extend(routes) or routes[0]
    return window


def test_entry_is_enabled_for_savegames_only(load_window, write_xml):
    assert load_window.actions.load_route_action.isEnabled()

    load_window.project_coordinator.load_xml_file(
        write_xml(x="0", y="0", z="0", out="", incoming="", flags="0")
    )
    assert not load_window.actions.load_route_action.isEnabled()
    assert not load_window.files.load_route_into_savegame()


def test_loads_a_route_of_the_map_as_one_undo_step_and_save_writes_it(load_window):
    load_window.answers = [QMessageBox.No]

    assert load_window.files.load_route_into_savegame()

    assert [entry.name for entry in load_window.offered] == ["Hof"]
    assert len(load_window.project_coordinator.autodrive_data.nodes) == 3
    assert load_window.isWindowModified()

    load_window.edit_history.undo()
    assert len(load_window.project_coordinator.autodrive_data.nodes) == 2

    load_window.edit_history.redo()
    load_window.files.save_xml()
    saved = AutoDriveXmlReader.load(load_window.savegame / "AutoDrive_config.xml")
    assert len(saved.nodes) == 3
    assert [marker.name for marker in saved.markers.values()] == ["Hof"]


def test_cancel_on_the_save_first_question_changes_nothing(load_window):
    load_window.answers = [QMessageBox.Cancel]

    assert not load_window.files.load_route_into_savegame()
    assert load_window.offered == []


def test_network_kept_in_a_route_is_not_asked_about(load_window):
    load_window.answers = [QMessageBox.No]
    load_window.files.load_route_into_savegame()

    load_window.files.load_route_into_savegame()

    assert load_window.answers == []
