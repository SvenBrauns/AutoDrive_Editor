"""Settings → Maps: import from a mod zip, re-import, remove, use for the open file."""

import zipfile

import pytest
from game_folder_helpers import add_routes, make_game_folder
from map_mod_helpers import make_single_map_mod
from PySide6.QtWidgets import QFileDialog

from autodrive_editor.file_io.map_mod import read_map_mod
from autodrive_editor.terrain.game_picture import PICTURE_FOLDER
from autodrive_editor.terrain.map_cache import MapCache

MAP_NAME = "LS25_Testkarte_2_0"


@pytest.fixture
def map_window(window, tmp_path, isolated_user_data, monkeypatch):
    folder = make_game_folder(tmp_path / "FarmingSimulator2025")
    window.settings.set_game_folder(folder)
    window.map_cache = window.map_import.map_cache = MapCache()
    window.messages = []
    monkeypatch.setattr(window.map_import, "_inform", window.messages.append)
    window.mods = folder / "mods"
    window.folder = folder
    return window


def test_failed_imports_are_reported(map_window, tmp_path):
    mod_path = make_single_map_mod(tmp_path / "elsewhere")
    map_mod = read_map_mod(mod_path)
    mod_path.unlink()  # the zip disappears before the import

    map_window.map_import._import_maps([(map_mod, map_mod.maps[0])])

    assert "Not imported" in map_window.messages[0]


def choose_file(monkeypatch, path):
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *args: (str(path), ""))


def test_import_from_mod_imports_all_its_maps(map_window, tmp_path, monkeypatch):
    choose_file(monkeypatch, make_single_map_mod(tmp_path / "elsewhere", title="Karte A"))

    map_window.map_import.import_map_mod()

    assert [m.title for m in map_window.map_cache.maps()] == ["Karte A"]
    assert map_window.messages == []


@pytest.mark.parametrize(
    ("content", "message"),
    [(b"no zip", "could not be read"), (None, "contains no map")],
)
def test_import_from_mod_explains_unusable_files(
    map_window, tmp_path, monkeypatch, content, message
):
    path = tmp_path / "FS25_Mod.zip"
    if content is None:
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("modDesc.xml", "<modDesc/>")
    else:
        path.write_bytes(content)
    choose_file(monkeypatch, path)

    map_window.map_import.import_map_mod()

    assert message in map_window.messages[0]
    assert map_window.map_cache.maps() == []


def test_reimport_reads_the_map_from_its_mod_again(map_window):
    mod = make_single_map_mod(map_window.mods, name="FS25_A", title="Karte A")
    cached = map_window.map_cache.import_map(mod, read_map_mod(mod).maps[0])
    (cached.directory / "dem.png").unlink()

    assert map_window.map_import.reimport(cached)

    assert cached.heightmap_path is not None


def test_reimport_without_the_mod_explains_it(map_window, tmp_path):
    mod = make_single_map_mod(tmp_path / "elsewhere", name="FS25_A")
    cached = map_window.map_cache.import_map(mod, read_map_mod(mod).maps[0])

    assert not map_window.map_import.reimport(cached)

    assert "FS25_A" in map_window.messages[0]


def test_remove_deletes_the_map_with_its_picture_after_asking(map_window, monkeypatch):
    mod = make_single_map_mod(map_window.mods, name="FS25_A")
    cached = map_window.map_cache.import_map(mod, read_map_mod(mod).maps[0])
    (cached.directory / PICTURE_FOLDER / "1").mkdir(parents=True)
    (cached.directory / PICTURE_FOLDER / "1" / "tile.webp").write_bytes(b"x" * 3_000_000)
    asked = []
    monkeypatch.setattr(
        map_window.map_import, "_confirm_remove", lambda name, size: asked.append(size) or True
    )

    assert map_window.map_import.remove(cached)

    assert asked == [3_000_000]
    assert not cached.directory.exists()


def test_removing_the_shown_map_takes_it_from_the_view(map_window, monkeypatch):
    mod = make_single_map_mod(map_window.mods, name="FS25_A")
    cached = map_window.map_cache.import_map(mod, read_map_mod(mod).maps[0])
    map_window.project_coordinator.map_cache = map_window.map_cache
    manager = add_routes(map_window.folder, [("R", "route.xml", MAP_NAME, 1)])
    map_window.project_coordinator.load_xml_file(manager / "routes" / "route.xml")
    assert map_window.background_map.has_background()
    monkeypatch.setattr(map_window.map_import, "_confirm_remove", lambda name, size: True)

    map_window.map_import.remove(cached)

    assert not map_window.background_map.has_background()


def test_map_chosen_for_the_open_file_is_shown_and_remembered(map_window, tmp_path, write_xml):
    mod = make_single_map_mod(map_window.mods, name="FS25_A")
    cached = map_window.map_cache.import_map(mod, read_map_mod(mod).maps[0])
    map_window.project_coordinator.map_cache = map_window.map_cache
    path = write_xml(x="0", y="0", z="0", out="", incoming="", flags="0")
    map_window.project_coordinator.load_xml_file(path)
    assert "choose one under File → Settings → Maps" in map_window.status.text()

    map_window.map_import.use_for_open_file(cached)
    assert map_window.background_map.has_background()

    map_window.project_coordinator.load_xml_file(path)
    assert map_window.background_map.has_background()


def test_map_menu_is_gone_and_capture_is_under_background(window):
    menus = {action.text(): action.menu() for action in window.menuBar().actions()}
    view = {action.text(): action.menu() for action in menus["View"].actions() if action.menu()}

    assert "Map" not in menus
    assert window.actions.capture_picture_action in view["Background"].actions()
    assert window.actions.refresh_picture_action in view["Background"].actions()
