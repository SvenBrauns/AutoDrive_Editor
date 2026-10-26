"""Importing maps from mods via the Karte menu."""

import pytest
from base_game_helpers import make_installation
from game_folder_helpers import make_game_folder
from map_mod_helpers import make_single_map_mod
from PySide6.QtCore import Qt

from autodrive_editor.file_io.map_mod import read_map_mod
from autodrive_editor.game.map_scanner import scan_for_map_mods
from autodrive_editor.terrain.map_cache import MapCache
from autodrive_editor.ui.dialogs.map_import_dialog import MapImportDialog


@pytest.fixture
def map_window(window, tmp_path, isolated_user_data, monkeypatch):
    folder = make_game_folder(tmp_path / "FarmingSimulator2025")
    window.settings.set_game_folder(folder)
    window.map_cache = MapCache()
    window.messages = []
    monkeypatch.setattr(window, "_inform", window.messages.append)
    window.mods = folder / "mods"
    return window


def test_scan_imports_the_chosen_maps(map_window, monkeypatch):
    make_single_map_mod(map_window.mods, name="FS25_A", title="Karte A")
    make_single_map_mod(map_window.mods, name="FS25_B", title="Karte B")
    monkeypatch.setattr(
        map_window,
        "_choose_maps_to_import",
        lambda result: [(m, e) for m in result.map_mods for e in m.maps if e.title == "Karte B"],
    )

    map_window.scan_map_mods()

    assert [m.title for m in map_window.map_cache.maps()] == ["Karte B"]
    assert map_window.status.text() == "1 map(s) imported"


def test_scan_without_map_mods_explains_it(map_window):
    map_window.mods.mkdir()

    map_window.scan_map_mods()

    assert "No map mods" in map_window.messages[0]


def test_failed_imports_are_reported(map_window, tmp_path):
    mod_path = make_single_map_mod(tmp_path / "elsewhere")
    map_mod = read_map_mod(mod_path)
    mod_path.unlink()  # the zip disappears before the import

    map_window._import_maps([(map_mod, map_mod.maps[0])])

    assert "Not imported" in map_window.messages[0]


def test_import_dialog_marks_imported_and_broken_maps(qapp, tmp_path, isolated_user_data):
    mods = tmp_path / "mods"
    make_single_map_mod(mods, name="FS25_Neu", title="Neu")
    old_path = make_single_map_mod(mods, name="FS25_Alt", title="Alt")
    make_single_map_mod(mods, name="FS25_Kaputt", title="Kaputt", width=3000)
    cache = MapCache()
    cache.import_map(old_path, read_map_mod(old_path).maps[0])

    dialog = MapImportDialog(scan_for_map_mods(mods).map_mods, cache)
    rows = {
        dialog.table.topLevelItem(i).text(0): dialog.table.topLevelItem(i)
        for i in range(dialog.table.topLevelItemCount())
    }

    assert rows["Alt"].text(3) == "already imported"
    assert rows["Neu"].text(3) == "new"
    assert "Map size" in rows["Kaputt"].text(3)
    assert not rows["Kaputt"].flags() & Qt.ItemFlag.ItemIsEnabled
    assert not dialog.import_button.isEnabled()

    dialog.select_new_maps()

    assert [entry.title for _, entry in dialog.chosen_maps] == ["Neu"]
    assert dialog.import_button.isEnabled()


def test_map_menu_offers_scan_and_import(window):
    map_menu = next(a.menu() for a in window.menuBar().actions() if a.text() == "Map")
    texts = [action.text() for action in map_menu.actions()]

    assert texts[:2] == ["Scan maps…", "Import map from mod…"]


def test_scan_lists_base_game_maps_first(map_window, tmp_path, monkeypatch):
    map_window.mods.mkdir()
    make_single_map_mod(map_window.mods, name="FS25_A", title="Karte A")
    map_window.settings.set_install_folder(make_installation(tmp_path / "FS25", folders=("mapUS",)))
    seen = []
    monkeypatch.setattr(
        map_window,
        "_choose_maps_to_import",
        lambda result: (
            seen.extend(result.map_mods)
            or [(m, e) for m in result.map_mods if m.is_base_game for e in m.maps]
        ),
    )

    map_window.scan_map_mods()

    assert [m.name for m in seen] == ["FS25 Grundspiel", "FS25_A"]
    assert [m.title for m in map_window.map_cache.maps()] == ["Riverbend Springs"]
