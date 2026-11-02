import json
import os

import pytest
from map_mod_helpers import (
    FRAME_COLOR,
    MAP_COLOR,
    make_single_map_mod,
    map_files,
    mod_desc,
    write_map_mod,
)
from PIL import Image

from autodrive_editor.file_io.ground_map import SURFACE_COLORS, Field
from autodrive_editor.file_io.map_mod import read_map_mod
from autodrive_editor.file_io.mod_archive import ModArchive
from autodrive_editor.terrain.map_cache import MapCache, map_stamp


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


def test_import_stores_ground_map_and_fields(cache, tmp_path):
    cached, _, _ = import_test_map(cache, tmp_path)

    assert Image.open(cached.ground_path).getpixel((0, 0)) == SURFACE_COLORS["asphalt"]
    assert MapCache().maps()[0].fields() == [Field(1, [(110, 220), (140, 220), (140, 250)])]


def test_maps_imported_before_have_no_ground_map(cache, tmp_path):
    cached, _, _ = import_test_map(cache, tmp_path)
    (cached.directory / "ground.png").unlink()
    (cached.directory / "fields.json").unlink()

    assert cached.ground_path is None
    assert cached.fields() == []


def test_a_broken_ground_texture_does_not_stop_the_import(cache, tmp_path):
    files = map_files()
    files["maps/data/asphalt01_weight.png"] = b"not a png"
    files["modDesc.xml"] = mod_desc([("SampleModMap", "maps/config/map.xml", {"de": "Karte"})])
    mod_path = write_map_mod(tmp_path / "FS25_Broken.zip", files)

    cached = cache.import_map(mod_path, read_map_mod(mod_path).maps[0])

    assert cached.overview_path.is_file()
    assert cached.ground_path is None


def test_imported_map_is_found_by_its_autodrive_name(cache, tmp_path):
    import_test_map(cache, tmp_path)

    found = MapCache().find("LS25_Testkarte_2_0")

    assert found.title == "LS25 Testkarte 2.0"
    assert found.map_scale == 2
    assert MapCache().find("Unbekannte_Karte") is None
    assert MapCache().find(None) is None


def test_cached_title_follows_the_editor_language(cache, tmp_path, german):
    cached, _, _ = import_test_map(cache, tmp_path)
    info_path = cached.directory / "map.json"
    info = json.loads(info_path.read_text(encoding="utf-8"))
    info["titles"] = {"en": "Test map", "de": "Testkarte"}
    info_path.write_text(json.dumps(info), encoding="utf-8")

    assert MapCache().maps()[0].title == "Testkarte"


def test_imports_from_older_versions_keep_their_title(cache, tmp_path):
    cached, _, _ = import_test_map(cache, tmp_path)
    info_path = cached.directory / "map.json"
    info = json.loads(info_path.read_text(encoding="utf-8"))
    del info["titles"]
    info_path.write_text(json.dumps(info), encoding="utf-8")

    assert MapCache().maps()[0].title == "LS25 Testkarte 2.0"


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

    with pytest.raises(ValueError, match="Map size"):
        cache.import_map(mod_path, entry)

    assert cache.maps() == []


def test_broken_cache_folders_are_skipped(cache, tmp_path):
    import_test_map(cache, tmp_path)
    (cache.directory / "broken").mkdir()
    (cache.directory / "broken" / "map.json").write_text("{not json", encoding="utf-8")

    assert len(cache.maps()) == 1


def test_import_stores_the_stamp_of_the_mod(cache, tmp_path):
    cached, mod_path, _ = import_test_map(cache, tmp_path)

    assert cached.source_stamp == (mod_path.stat().st_size, mod_path.stat().st_mtime_ns)
    assert cached.declined_stamp is None


def test_stamp_of_an_unpacked_mod_comes_from_the_map_files(cache, tmp_path):
    cached, mod_path, entry = import_test_map(cache, tmp_path, unpacked=True)
    image = mod_path / entry.image_file
    os.utime(image, ns=(0, 10**18))

    with ModArchive(mod_path) as archive:
        assert len(cached.source_stamp) == 6
        assert map_stamp(archive, entry) != cached.source_stamp


def test_recorded_and_declined_stamps_are_kept_in_the_info(cache, tmp_path):
    cached, _, _ = import_test_map(cache, tmp_path)

    cache.record_stamp(cached, (1, 2))
    declined = cache.decline_update(cached, (3, 4))

    assert (declined.source_stamp, declined.declined_stamp) == ((1, 2), (3, 4))
    assert MapCache().maps()[0] == declined
