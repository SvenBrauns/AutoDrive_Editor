"""Setup dialog on first start."""

import pytest
from base_game_helpers import make_installation

from autodrive_editor.settings.app_settings import AppSettings
from autodrive_editor.terrain.map_cache import MapCache

MAP_NAME = "LS25_Testkarte_2_0"


@pytest.fixture
def setup_window(window, tmp_path, isolated_user_data, monkeypatch):

    window.settings = window.files.settings = window.map_import.settings = AppSettings()
    cache = MapCache()
    window.map_cache = window.map_import.map_cache = cache
    window.project_coordinator.map_cache = cache
    window.scans = []
    monkeypatch.setattr(window.map_import, "scan_map_mods", lambda: window.scans.append(True))
    return window


def test_first_start_shows_setup_and_scans(setup_window, monkeypatch):
    shown = []
    monkeypatch.setattr(
        setup_window.map_import, "_show_first_start_dialog", lambda: shown.append(1) or True
    )

    setup_window.map_import.run_first_start()
    setup_window.map_import.run_first_start()

    assert shown == [1]
    assert setup_window.scans == [True]
    assert not setup_window.settings.needs_setup


def test_skipped_setup_does_not_scan_and_is_not_shown_again(setup_window, monkeypatch):
    monkeypatch.setattr(setup_window.map_import, "_show_first_start_dialog", lambda: False)

    setup_window.map_import.run_first_start()

    assert setup_window.scans == []
    assert not setup_window.settings.needs_setup


def test_scan_works_with_only_the_install_folder(window, tmp_path, isolated_user_data, monkeypatch):

    window.settings = window.files.settings = window.map_import.settings = AppSettings()
    window.settings.set_install_folder(make_installation(tmp_path / "FS25", folders=("mapEU",)))
    window.map_cache = window.map_import.map_cache = MapCache()
    offered = []
    monkeypatch.setattr(
        window.map_import,
        "_choose_maps_to_import",
        lambda result: offered.extend(result.map_mods) or [],
    )

    window.map_import.scan_map_mods()

    assert [m.name for m in offered] == ["FS25 Grundspiel"]
