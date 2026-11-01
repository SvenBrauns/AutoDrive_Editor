from base_game_helpers import make_installation
from map_mod_helpers import make_single_map_mod

from autodrive_editor.file_io.base_game_maps import read_base_game_maps
from autodrive_editor.game.map_source import find_by_map_id, find_by_map_name, split_map_id


def test_map_id_names_mod_and_map_or_a_base_game_map():
    assert split_map_id("FS25_Thueringen.SampleModMap") == ("FS25_Thueringen", "SampleModMap")
    assert split_map_id("MapUS") == (None, "MapUS")


def test_map_id_finds_the_zipped_or_unpacked_mod(tmp_path):
    make_single_map_mod(tmp_path / "mods", name="FS25_A")
    make_single_map_mod(tmp_path / "mods", name="FS25_B", unpacked=True)

    for mod_name in ("FS25_A", "FS25_B"):
        mod, entry = find_by_map_id(f"{mod_name}.SampleModMap", tmp_path / "mods", None)
        assert (mod.name, entry.map_id) == (mod_name, "SampleModMap")


def test_map_id_of_a_missing_mod_or_map_finds_nothing(tmp_path):
    make_single_map_mod(tmp_path / "mods", name="FS25_A")

    assert find_by_map_id("FS25_Gone.SampleModMap", tmp_path / "mods", None) is None
    assert find_by_map_id("FS25_A.OtherMap", tmp_path / "mods", None) is None


def test_map_id_without_mod_is_a_base_game_map(tmp_path):
    base = read_base_game_maps(make_installation(tmp_path / "FS25", folders=("mapUS",)) / "data")

    _, entry = find_by_map_id("MapUS", tmp_path / "mods", base)

    assert entry.map_id == "mapUS"


def test_map_name_is_looked_for_in_all_mods(tmp_path):
    make_single_map_mod(tmp_path / "mods", name="FS25_Other", title="Andere Karte")
    make_single_map_mod(tmp_path / "mods", name="FS25_Test")

    mod, _ = find_by_map_name("LS25_Testkarte_2_0", tmp_path / "mods", None)

    assert mod.name == "FS25_Test"
    assert find_by_map_name("Unbekannt", tmp_path / "mods", None) is None
