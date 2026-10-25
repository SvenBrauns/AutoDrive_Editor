from map_mod_helpers import make_single_map_mod, write_map_mod

from autodrive_editor.game.map_scanner import scan_for_map_mods


def test_finds_zipped_and_unpacked_map_mods(tmp_path):
    mods = tmp_path / "mods"
    make_single_map_mod(mods, name="FS25_Zip")
    make_single_map_mod(mods, name="FS25_Folder", unpacked=True)
    write_map_mod(mods / "FS25_Tractor.zip", {"modDesc.xml": "<modDesc/>"})

    result = scan_for_map_mods(mods)

    assert [mod.name for mod in result.map_mods] == ["FS25_Folder", "FS25_Zip"]
    assert result.skipped == []


def test_unreadable_mods_are_skipped_and_reported(tmp_path):
    mods = tmp_path / "mods"
    make_single_map_mod(mods, name="FS25_Good")
    write_map_mod(mods / "FS25_Broken.zip", {"modDesc.xml": "<modDesc"})
    (mods / "not_a_zip.zip").write_bytes(b"nothing")

    result = scan_for_map_mods(mods)

    assert [mod.name for mod in result.map_mods] == ["FS25_Good"]
    assert sorted(name for name, _ in result.skipped) == ["FS25_Broken.zip", "not_a_zip.zip"]


def test_missing_mods_folder_gives_empty_result(tmp_path):
    result = scan_for_map_mods(tmp_path / "missing")

    assert result.map_mods == [] and result.skipped == []
