"""Opening a route or savegame loads the matching imported map."""

import pytest
from game_folder_helpers import add_routes, add_savegame, make_game_folder
from map_mod_helpers import heightmap_png, make_single_map_mod

from autodrive_editor.file_io.map_mod import read_map_mod
from autodrive_editor.terrain.map_cache import MapCache

MAP_NAME = "LS25_Testkarte_2_0"  # AutoDrive name of "LS25 Testkarte 2.0"


@pytest.fixture
def map_window(window, tmp_path, isolated_user_data):
    folder = make_game_folder(tmp_path / "FarmingSimulator2025")
    window.settings.set_game_folder(folder)

    cache = MapCache()
    window.map_cache = window.map_import.map_cache = cache
    window.project_coordinator.map_cache = cache

    window.folder = folder
    window.tmp = tmp_path
    return window


def import_test_map(window):
    mod_path = make_single_map_mod(window.tmp / "mods")
    return window.map_cache.import_map(mod_path, read_map_mod(mod_path).maps[0])


def open_route(window, map_name):
    manager = add_routes(window.folder, [("Testroute", "route.xml", map_name, 1)])
    window.project_coordinator.load_xml_file(manager / "routes" / "route.xml")


def test_route_loads_its_imported_map(map_window):
    cached = import_test_map(map_window)

    open_route(map_window, MAP_NAME)

    assert map_window.background_map.file_path == str(cached.overview_path)
    assert map_window.background_map.has_background()
    assert map_window.background_map.map_scale == 2
    assert map_window.heightmap.has_heightmap()
    assert map_window.project_coordinator.current_heightmap_path == str(cached.heightmap_path)
    assert "map “LS25 Testkarte 2.0”" in map_window.status.text()


def test_map_size_menu_follows_the_detected_map(map_window):
    import_test_map(map_window)

    open_route(map_window, MAP_NAME)

    assert map_window.actions.map_scale_actions[2].isChecked()


def test_savegame_prefers_its_own_heightmap(map_window):
    import_test_map(map_window)
    savegame = add_savegame(map_window.folder, 1, "Spielstand", "LS25 Testkarte 2.0", MAP_NAME)
    (savegame / "terrain.heightmap.png").write_bytes(heightmap_png())

    map_window.project_coordinator.load_xml_file(savegame / "AutoDrive_config.xml")

    assert map_window.project_coordinator.current_heightmap_path == str(
        (savegame / "terrain.heightmap.png").resolve()
    )


def test_map_that_is_not_imported_is_named_in_the_status(map_window):
    open_route(map_window, "Unbekannte_Karte")

    assert not map_window.background_map.has_background()
    assert "“Unbekannte_Karte” is not imported" in map_window.status.text()
    assert "Scan maps" in map_window.status.text()


def test_without_map_name_nothing_is_detected(map_window, write_xml):
    import_test_map(map_window)

    map_window.project_coordinator.load_xml_file(write_xml())

    assert not map_window.background_map.has_background()
    assert "not imported" not in map_window.status.text()


def test_project_files_keep_their_own_map(map_window):
    import_test_map(map_window)
    manager = add_routes(map_window.folder, [("Testroute", "route.xml", MAP_NAME, 1)])

    map_window.project_coordinator.load_xml_file(manager / "routes" / "route.xml", detect_map=False)

    assert not map_window.background_map.has_background()
