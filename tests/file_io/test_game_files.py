import zipfile

import pytest

from autodrive_editor.file_io.game_files import GameFiles, locate


@pytest.mark.parametrize(
    ("name", "mod", "expected"),
    [
        ("data/placeables/shed.xml", None, (None, "data/placeables/shed.xml")),
        ("$data/placeables/shed.i3d", "FS25_Mod", (None, "data/placeables/shed.i3d")),
        ("$moddir$FS25_Mod/xml/shed.xml", None, ("FS25_Mod", "xml/shed.xml")),
        (r"i3d\shed.i3d", "FS25_Mod", ("FS25_Mod", "i3d/shed.i3d")),
    ],
)
def test_locate_finds_the_mod_and_path_of_a_game_file_name(name, mod, expected):
    assert locate(name, mod) == expected


def test_reads_from_the_install_folder_a_zipped_mod_and_an_unpacked_mod(tmp_path):
    (tmp_path / "game/data").mkdir(parents=True)
    (tmp_path / "game/data/a.xml").write_bytes(b"game")
    (tmp_path / "mods/FS25_Folder").mkdir(parents=True)
    (tmp_path / "mods/FS25_Folder/b.xml").write_bytes(b"folder")
    with zipfile.ZipFile(tmp_path / "mods/FS25_Zip.zip", "w") as archive:
        archive.writestr("c.xml", "zip")

    with GameFiles(tmp_path / "game", tmp_path / "mods") as files:
        assert files.read(None, "data/a.xml") == b"game"
        assert files.read("FS25_Folder", "b.xml") == b"folder"
        assert files.read("FS25_Zip", "C.xml") == b"zip"


def test_missing_folders_and_mods_raise_file_not_found(tmp_path):
    with GameFiles(None, None) as files:
        with pytest.raises(FileNotFoundError):
            files.read(None, "data/a.xml")
        with pytest.raises(FileNotFoundError):
            files.read("FS25_Mod", "a.xml")

    with GameFiles(None, tmp_path) as files, pytest.raises(FileNotFoundError):
        files.read("FS25_Missing", "a.xml")
