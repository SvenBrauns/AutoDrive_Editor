import pytest
from game_folder_helpers import make_game_folder
from map_mod_helpers import make_single_map_mod

from autodrive_editor.file_io.map_mod import read_map_mod
from autodrive_editor.terrain.map_cache import MapCache
from autodrive_editor.ui.dialogs.maps_widget import MapsWidget


@pytest.fixture
def maps_window(window, tmp_path, isolated_user_data):
    window.settings.set_game_folder(make_game_folder(tmp_path / "FarmingSimulator2025"))
    window.map_cache = window.map_import.map_cache = MapCache()
    mod = make_single_map_mod(tmp_path / "mods", title="Karte A")
    window.map_cache.import_map(mod, read_map_mod(mod).maps[0])
    return window


def test_lists_the_imported_maps(maps_window):
    widget = MapsWidget(maps_window.map_import)
    row = widget.table.topLevelItem(0)

    assert [row.text(column) for column in range(5)] == [
        "Karte A",
        "FS25_Testkarte",
        "4 km",
        "yes",
        "–",
    ]


def test_buttons_need_a_selected_map_and_use_needs_an_open_file(maps_window, write_xml):
    widget = MapsWidget(maps_window.map_import)
    assert not widget.remove_button.isEnabled()

    widget.table.setCurrentItem(widget.table.topLevelItem(0))
    assert widget.remove_button.isEnabled()
    assert not widget.use_button.isEnabled()

    maps_window.project_coordinator.load_xml_file(
        write_xml(x="0", y="0", z="0", out="", incoming="", flags="0")
    )
    widget.refresh()
    widget.table.setCurrentItem(widget.table.topLevelItem(0))
    assert widget.use_button.isEnabled()


def test_removed_map_leaves_the_list(maps_window, monkeypatch):
    monkeypatch.setattr(maps_window.map_import, "_confirm_remove", lambda name, size: True)
    widget = MapsWidget(maps_window.map_import)
    widget.table.setCurrentItem(widget.table.topLevelItem(0))

    widget.remove_button.click()

    assert widget.table.topLevelItemCount() == 0


def test_several_maps_can_be_reimported_but_only_one_removed(maps_window, tmp_path, monkeypatch):
    mod = make_single_map_mod(tmp_path / "mods", name="FS25_B", title="Karte B")
    maps_window.map_cache.import_map(mod, read_map_mod(mod).maps[0])
    reimported = []
    monkeypatch.setattr(maps_window.map_import, "reimport", reimported.append)
    widget = MapsWidget(maps_window.map_import)

    widget.table.selectAll()

    assert widget.reimport_button.isEnabled()
    assert not widget.remove_button.isEnabled()
    widget.reimport_button.click()
    assert [cached.title for cached in reimported[0]] == ["Karte A", "Karte B"]
