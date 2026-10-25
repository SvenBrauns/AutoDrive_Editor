"""Setup dialog on first start and the question about missing maps."""

import pytest
from base_game_helpers import make_installation
from game_folder_helpers import add_routes, make_game_folder
from map_mod_helpers import make_single_map_mod

from autodrive_editor.file_io.map_mod import read_map_mod
from autodrive_editor.settings.app_settings import AppSettings
from autodrive_editor.terrain.map_cache import MapCache

MAP_NAME = "LS25_Testkarte_2_0"


@pytest.fixture
def setup_window(window, tmp_path, isolated_user_data, monkeypatch):

    window.settings = AppSettings()
    cache = MapCache()
    window.map_cache = cache
    window.project_coordinator.map_cache = cache
    window.scans = []
    monkeypatch.setattr(window, "scan_map_mods", lambda: window.scans.append(True))
    return window


def test_first_start_shows_setup_and_scans(setup_window, monkeypatch):
    shown = []
    monkeypatch.setattr(setup_window, "_show_first_start_dialog", lambda: shown.append(1) or True)

    setup_window.run_first_start()
    setup_window.run_first_start()

    assert shown == [1]
    assert setup_window.scans == [True]
    assert not setup_window.settings.needs_setup


def test_skipped_setup_does_not_scan_and_is_not_shown_again(setup_window, monkeypatch):
    monkeypatch.setattr(setup_window, "_show_first_start_dialog", lambda: False)

    setup_window.run_first_start()

    assert setup_window.scans == []
    assert not setup_window.settings.needs_setup


@pytest.fixture
def route_window(setup_window, tmp_path):
    folder = make_game_folder(tmp_path / "FarmingSimulator2025")
    setup_window.settings.set_game_folder(folder)
    setup_window.questions = []
    setup_window.answer = None

    def ask(map_name):
        setup_window.questions.append(map_name)
        return setup_window.answer

    setup_window._ask_missing_map = ask

    def open_route():
        manager = add_routes(folder, [("Testroute", "route.xml", MAP_NAME, 1)])
        setup_window.project_coordinator.load_xml_file(manager / "routes" / "route.xml")

    setup_window.open_route_file = open_route
    return setup_window


def test_missing_map_is_asked_for(route_window):
    route_window.open_route_file()

    assert route_window.questions == [MAP_NAME]


def test_declined_map_is_not_asked_again(route_window):
    route_window.open_route_file()
    route_window.open_route_file()

    assert route_window.questions == [MAP_NAME]


def test_imported_map_is_not_asked_for(route_window, tmp_path):
    mod = make_single_map_mod(tmp_path / "mods")

    route_window.map_cache.import_map(mod, read_map_mod(mod).maps[0])
    route_window.open_route_file()

    assert route_window.questions == []


def test_map_scanned_from_the_question_is_loaded(route_window, tmp_path, monkeypatch):
    mod = make_single_map_mod(tmp_path / "mods")

    def scan():
        route_window.map_cache.import_map(mod, read_map_mod(mod).maps[0])

    monkeypatch.setattr(route_window, "scan_map_mods", scan)
    route_window.answer = route_window.MISSING_MAP_SCAN

    route_window.open_route_file()

    assert route_window.background_map.background_item is not None
    assert "Karte geladen" in route_window.status.text()


def test_scan_works_with_only_the_install_folder(window, tmp_path, isolated_user_data, monkeypatch):

    window.settings = AppSettings()
    window.settings.set_install_folder(make_installation(tmp_path / "FS25", folders=("mapEU",)))
    window.map_cache = MapCache()
    offered = []
    monkeypatch.setattr(
        window, "_choose_maps_to_import", lambda result: offered.extend(result.map_mods) or []
    )

    window.scan_map_mods()

    assert [m.name for m in offered] == ["FS25 Grundspiel"]
