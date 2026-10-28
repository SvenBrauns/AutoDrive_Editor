from game_folder_helpers import add_savegame, make_game_folder

from autodrive_editor.game.game_folder import GameFolder
from autodrive_editor.game.savegame_info import read_savegame_info, savegames_with_autodrive


def test_reads_name_map_and_date(tmp_path):
    directory = add_savegame(tmp_path, 3, "Mein Spielstand", "LS25 Thüringen 2.0 16x", "LS25_X")

    info = read_savegame_info(directory)

    assert (info.number, info.name, info.map_title, info.save_date) == (
        3,
        "Mein Spielstand",
        "LS25 Thüringen 2.0 16x",
        "23.10.2026",
    )
    assert info.autodrive_config_path == directory / "AutoDrive_config.xml"


def test_savegame_without_career_file_gets_a_default_name(tmp_path):
    directory = tmp_path / "savegame7"
    directory.mkdir()

    assert read_savegame_info(directory).display_name == "Savegame 7"


def test_only_savegames_with_autodrive_are_listed(tmp_path):
    folder = make_game_folder(tmp_path / "fs")
    add_savegame(folder, 10, "Zehn", "Map", "Map_A")
    add_savegame(folder, 2, "Zwei", "Map", "Map_B")
    add_savegame(folder, 1, "Ohne AutoDrive", "Map", "", with_autodrive=False)

    listed = savegames_with_autodrive(GameFolder(folder))

    assert [info.name for info in listed] == ["Zwei", "Zehn"]


def test_autodrive_map_name_is_the_name_routes_xml_uses(tmp_path):
    directory = add_savegame(tmp_path, 3, "Hof", "LS25 Thüringen 2.0 16x", "LS25_X")

    assert read_savegame_info(directory).autodrive_map_name == "LS25_Thüringen_2_0_16x"
