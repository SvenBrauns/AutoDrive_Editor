import json

import pytest
from map_mod_helpers import FRAME_COLOR, MAP_COLOR, make_single_map_mod
from PIL import Image

from autodrive_editor.file_io.map_mod import read_map_mod
from autodrive_editor.terrain.map_cache import MapCache


@pytest.fixture
def cache(isolated_user_data):
    return MapCache()


def import_test_map(cache, tmp_path, **options):
    mod_path = make_single_map_mod(tmp_path / "mods", **options)
    entry = read_map_mod(mod_path).maps[0]
    return cache.import_map(mod_path, entry), mod_path, entry


def test_cache_lives_in_the_user_data_folder(cache, isolated_user_data):
    assert cache.directory == isolated_user_data / "maps"
    assert cache.maps() == []


def test_import_stores_cropped_map_image_heightmap_and_info(cache, tmp_path):
    cached, _, _ = import_test_map(cache, tmp_path)

    image = Image.open(cached.overview_path).convert("RGBA")
    assert image.size == (2048, 2048)
    assert image.getpixel((5, 5)) == MAP_COLOR  # frame cut away
    assert FRAME_COLOR not in {image.getpixel((0, 0)), image.getpixel((2047, 2047))}
    assert Image.open(cached.heightmap_path).mode.startswith("I")

    info = json.loads((cached.directory / "map.json").read_text(encoding="utf-8"))
    assert info["autodrive_names"] == ["LS25_Testkarte_2_0"]
    assert info["map_scale"] == 2
    assert info["mod_name"] == "FS25_Testkarte"


def test_imported_map_is_found_by_its_autodrive_name(cache, tmp_path):
    import_test_map(cache, tmp_path)

    found = MapCache().find("LS25_Testkarte_2_0")

    assert found.title == "LS25 Testkarte 2.0"
    assert found.map_scale == 2
    assert MapCache().find("Unbekannte_Karte") is None
    assert MapCache().find(None) is None


def test_importing_again_replaces_the_earlier_import(cache, tmp_path):
    first, mod_path, entry = import_test_map(cache, tmp_path)

    second = cache.import_map(mod_path, entry)

    assert second.directory == first.directory
    assert len(cache.maps()) == 1


def test_different_maps_with_the_same_name_get_separate_folders(cache, tmp_path):
    first, _, _ = import_test_map(cache, tmp_path / "a", name="FS25_A")
    second, _, _ = import_test_map(cache, tmp_path / "b", name="FS25_B")

    assert first.directory != second.directory
    assert len(cache.maps()) == 2


def test_find_import_tells_whether_a_map_was_imported(cache, tmp_path):
    mod_path = make_single_map_mod(tmp_path / "mods")
    entry = read_map_mod(mod_path).maps[0]
    assert cache.find_import("FS25_Testkarte", entry) is None

    cache.import_map(mod_path, entry)

    assert cache.find_import("FS25_Testkarte", entry) is not None


def test_maps_with_problems_are_not_imported(cache, tmp_path):
    mod_path = make_single_map_mod(tmp_path / "mods", width=3000)
    entry = read_map_mod(mod_path).maps[0]

    with pytest.raises(ValueError, match="Kartengröße"):
        cache.import_map(mod_path, entry)

    assert cache.maps() == []


def test_broken_cache_folders_are_skipped(cache, tmp_path):
    import_test_map(cache, tmp_path)
    (cache.directory / "broken").mkdir()
    (cache.directory / "broken" / "map.json").write_text("{not json", encoding="utf-8")

    assert len(cache.maps()) == 1
