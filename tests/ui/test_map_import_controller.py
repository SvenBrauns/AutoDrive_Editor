"""A missing map is imported without asking when a file is opened."""

import json
import os

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


@pytest.fixture
def update_window(import_window):
    """A savegame open on its imported map; _ask_update gives the answers in window.answers."""

    import_window.mod_path = make_single_map_mod(import_window.folder / "mods", name="FS25_Test")
    open_savegame(import_window)
    import_window.answers, import_window.asked = [], []

    def ask(title):
        import_window.asked.append(title)
        return import_window.answers.pop(0)

    import_window.map_import._ask_update = ask
    return import_window


def update_mod(window):
    os.utime(window.mod_path, ns=(0, window.mod_path.stat().st_mtime_ns + 10**9))


def cached_map(window):
    return window.map_cache.find(MAP_NAME)


def test_unchanged_mod_is_not_offered_again(update_window):
    update_window.map_import.offer_update()

    assert update_window.asked == []


def test_updated_mod_is_imported_again_when_wanted(update_window):
    update_mod(update_window)
    update_window.answers = ["import"]

    update_window.map_import.offer_update()
    update_window.map_import.offer_update()

    assert update_window.asked == ["LS25 Testkarte 2.0"]
    assert cached_map(update_window).source_stamp[1] == update_window.mod_path.stat().st_mtime_ns


def test_update_not_now_is_asked_again_only_in_the_next_session(update_window):
    update_mod(update_window)
    update_window.answers = ["later", "later"]

    update_window.map_import.offer_update()
    update_window.map_import.offer_update()
    update_window.map_import.postponed_updates.clear()
    update_window.map_import.offer_update()

    assert len(update_window.asked) == 2


def test_update_declined_for_this_version_is_asked_again_after_the_next_change(update_window):
    update_mod(update_window)
    update_window.answers = ["never", "later"]

    update_window.map_import.offer_update()
    update_window.map_import.offer_update()
    update_mod(update_window)
    update_window.map_import.offer_update()

    assert len(update_window.asked) == 2


def test_import_of_an_older_version_records_the_stamp_without_asking(update_window):
    cached = cached_map(update_window)
    info_path = cached.directory / "map.json"
    info = json.loads(info_path.read_text(encoding="utf-8"))
    del info["source_stamp"]
    info_path.write_text(json.dumps(info), encoding="utf-8")
    update_mod(update_window)

    update_window.map_import.offer_update()

    assert update_window.asked == []
    assert cached_map(update_window).source_stamp is not None


def test_update_is_offered_after_a_file_was_opened(update_window):
    update_mod(update_window)
    update_window.answers = ["later"]

    update_window.files._load_config(update_window.project_coordinator.config_source.path)

    assert update_window.asked == ["LS25 Testkarte 2.0"]
