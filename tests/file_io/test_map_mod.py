import pytest
from map_mod_helpers import make_single_map_mod, map_files, mod_desc, write_map_mod

from autodrive_editor.file_io.map_mod import autodrive_map_name, read_map_mod


@pytest.mark.parametrize(
    ("title", "name"),
    [
        ("LS25 Thüringen 2.0 16x", "LS25_Thüringen_2_0_16x"),
        ("NF Marsch 4fach oG", "NF_Marsch_4fach_oG"),
        ("Papenburger_Map_v2_4k", "Papenburger_Map_v2_4k"),
    ],
)
def test_autodrive_map_name_matches_real_names(title, name):
    assert autodrive_map_name(title) == name


@pytest.mark.parametrize("unpacked", [False, True])
def test_reads_map_from_zip_and_folder(tmp_path, unpacked):
    mod_path = make_single_map_mod(tmp_path, unpacked=unpacked)

    mod = read_map_mod(mod_path)

    entry = mod.maps[0]
    assert mod.name == "FS25_Testkarte"
    assert entry.title == "LS25 Testkarte 2.0"
    assert entry.autodrive_names == ["LS25_Testkarte_2_0"]
    assert entry.map_scale == 2
    assert entry.image_file == "maps/overview.dds"  # config names .png
    assert entry.heightmap_file == "maps/data/dem.png"
    assert entry.problems == []


def test_two_maps_in_one_mod_get_their_own_heightmaps(tmp_path):
    files = {
        **map_files(folder="a", data_folder="data"),
        **map_files(folder="b", data_folder="dataFE"),
    }
    files["modDesc.xml"] = mod_desc(
        [
            ("normal", "a/config/map.xml", {"en": "Island", "de": "Insel"}),
            ("farmer", "b/config/map.xml", {"en": "Island Farmer Edition"}),
        ]
    )

    mod = read_map_mod(write_map_mod(tmp_path / "FS25_Island.zip", files))

    assert [m.heightmap_file for m in mod.maps] == ["a/data/dem.png", "b/dataFE/dem.png"]
    assert mod.maps[0].title == "Insel"  # German preferred
    assert mod.maps[0].autodrive_names == ["Island", "Insel"]  # every language


def test_mod_without_map_is_ignored(tmp_path):
    path = write_map_mod(tmp_path / "FS25_Tractor.zip", {"modDesc.xml": "<modDesc/>"})

    assert read_map_mod(path) is None


def test_unsupported_size_and_missing_image_are_reported(tmp_path):
    files = map_files(width=3000)
    del files["maps/overview.dds"]
    files["modDesc.xml"] = mod_desc([("m", "maps/config/map.xml", {"en": "Odd"})])

    entry = read_map_mod(write_map_mod(tmp_path / "FS25_Odd.zip", files)).maps[0]

    assert entry.map_scale is None
    assert len(entry.problems) == 2
