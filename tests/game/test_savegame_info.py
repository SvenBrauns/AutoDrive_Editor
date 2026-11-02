import os
from datetime import datetime

from game_folder_helpers import add_savegame, make_game_folder

from autodrive_editor.game.game_folder import GameFolder
from autodrive_editor.game.savegame_info import read_savegame_info, savegames


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

    assert read_savegame_info(directory).display_name == "savegame7"


def test_display_name_starts_with_the_folder(tmp_path):
    directory = add_savegame(tmp_path, 3, "Mein Spielstand", "LS25 Thüringen 2.0 16x", "LS25_X")

    assert read_savegame_info(directory).display_name == "savegame3 – Mein Spielstand"


def test_autodrive_map_name_is_the_name_routes_xml_uses(tmp_path):
    directory = add_savegame(tmp_path, 3, "Hof", "LS25 Thüringen 2.0 16x", "LS25_X")

    assert read_savegame_info(directory).autodrive_map_name == "LS25_Thüringen_2_0_16x"


def test_all_savegames_are_listed_newest_first_without_empty_slots(tmp_path):
    folder = make_game_folder(tmp_path / "fs")
    old = add_savegame(folder, 1, "Alt", "Map", "Map_A")
    add_savegame(folder, 2, "Ohne AutoDrive", "Map", "", with_autodrive=False)
    (folder / "savegame3").mkdir()
    os.utime(old / "careerSavegame.xml", (1_000_000, 1_000_000))

    listed = savegames(GameFolder(folder))

    assert [(info.name, info.has_autodrive) for info in listed] == [
        ("Ohne AutoDrive", False),
        ("Alt", True),
    ]
    assert listed[1].saved_text == datetime.fromtimestamp(1_000_000).strftime("%Y-%m-%d %H:%M")
