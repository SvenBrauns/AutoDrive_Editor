"""A missing map is imported without asking when a file is opened."""

import pytest
from game_folder_helpers import add_routes, add_savegame, make_game_folder
from map_mod_helpers import make_single_map_mod
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from autodrive_editor.terrain.map_cache import MapCache

MAP_NAME = "LS25_Testkarte_2_0"  # AutoDrive name of "LS25 Testkarte 2.0"


@pytest.fixture
def import_window(window, tmp_path, isolated_user_data):
    folder = make_game_folder(tmp_path / "FarmingSimulator2025")
    window.settings.set_game_folder(folder)
    cache = MapCache()
    window.map_cache = window.map_import.map_cache = window.project_coordinator.map_cache = cache
    window.folder = folder
    window.questions = []
    window.map_import._ask_map_not_found = lambda name: window.questions.append(name)
    return window


def open_savegame(window):
    savegame = add_savegame(window.folder, 1, "Hof", "LS25 Testkarte 2.0", MAP_NAME)
    window.project_coordinator.load_xml_file(savegame / "AutoDrive_config.xml")


def open_route(window, map_name=MAP_NAME):
    manager = add_routes(window.folder, [("Testroute", "route.xml", map_name, 1)])
    window.project_coordinator.load_xml_file(manager / "routes" / "route.xml")


def test_savegame_imports_the_mod_its_map_id_names(import_window):
    # add_savegame writes the mapId FS25_Test.SampleModMap.
    make_single_map_mod(import_window.folder / "mods", name="FS25_Test")

    open_savegame(import_window)

    assert import_window.map_cache.find(MAP_NAME) is not None
    assert import_window.background_map.has_background()
    assert import_window.questions == []


def test_route_imports_the_mod_with_its_map_name(import_window):
    make_single_map_mod(import_window.folder / "mods", name="FS25_Testkarte")

    open_route(import_window)

    assert import_window.background_map.has_background()
    assert import_window.questions == []


def test_map_not_found_is_asked_for_once_per_session(import_window):
    open_route(import_window)
    open_route(import_window)

    assert import_window.questions == [MAP_NAME]
    assert not import_window.background_map.has_background()


def test_imported_map_is_not_looked_for(import_window, monkeypatch):
    make_single_map_mod(import_window.folder / "mods", name="FS25_Testkarte")
    open_route(import_window)
    monkeypatch.setattr(import_window.map_import, "_find_map", lambda source: 1 / 0)

    open_route(import_window)

    assert import_window.background_map.has_background()


def test_without_a_map_the_size_follows_the_network(import_window):
    make_single_map_mod(import_window.folder / "mods", name="FS25_Testkarte")
    open_route(import_window)
    assert import_window.background_map.map_scale == 2

    open_route(import_window, "Unbekannte_Karte")

    assert not import_window.background_map.has_background()
    assert not import_window.heightmap.has_heightmap()
    assert import_window.background_map.map_scale == 1


def test_map_not_found_is_asked_with_a_normal_cursor_while_loading(import_window):
    cursors = []
    import_window.map_import._ask_map_not_found = lambda name: cursors.append(
        QApplication.overrideCursor().shape()
    )

    with import_window.view.busy("Loading"):
        open_route(import_window)

    assert cursors == [Qt.ArrowCursor]
