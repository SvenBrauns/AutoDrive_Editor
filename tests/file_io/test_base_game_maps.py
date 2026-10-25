from base_game_helpers import make_installation

from autodrive_editor.file_io.base_game_maps import BASE_GAME_MOD_NAME, read_base_game_maps
from autodrive_editor.terrain.map_cache import MapCache


def test_base_maps_are_read_with_their_titles(tmp_path):
    install = make_installation(tmp_path / "FS25")

    mod = read_base_game_maps(install / "data")

    assert mod.is_base_game
    assert mod.name == BASE_GAME_MOD_NAME
    assert [entry.title for entry in mod.maps] == ["Riverbend Springs", "Zielonka", "Hutan Pantai"]
    assert "Riverbend_Springs" in mod.maps[0].autodrive_names


def test_data_paths_lead_to_image_and_heightmap(tmp_path):
    install = make_installation(tmp_path / "FS25", folders=("mapUS",))

    entry = read_base_game_maps(install / "data").maps[0]

    assert entry.image_file == "maps/mapUS/textures/ui/overview.dds"
    assert entry.heightmap_file == "maps/mapUS/data/dem.png"
    assert entry.map_scale == 1
    assert entry.problems == []


def test_missing_base_maps_are_skipped(tmp_path):
    install = make_installation(tmp_path / "FS25", folders=("mapEU",))

    assert [entry.map_id for entry in read_base_game_maps(install / "data").maps] == ["mapEU"]


def test_no_base_maps_gives_none(tmp_path):
    (tmp_path / "data").mkdir()

    assert read_base_game_maps(tmp_path / "data") is None


def test_base_map_can_be_imported(tmp_path, isolated_user_data):
    install = make_installation(tmp_path / "FS25", folders=("mapAS",))
    mod = read_base_game_maps(install / "data")

    cached = MapCache().import_map(mod, mod.maps[0])

    assert cached.title == "Hutan Pantai"
    assert cached.overview_path.is_file()
    assert cached.heightmap_path.is_file()
    assert MapCache().find("Hutan_Pantai").title == "Hutan Pantai"
