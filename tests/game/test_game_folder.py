from game_folder_helpers import make_game_folder

from autodrive_editor.game.game_folder import GameFolder


def test_folder_with_game_xml_is_valid(tmp_path):
    assert GameFolder(make_game_folder(tmp_path / "FarmingSimulator2025")).is_valid


def test_other_folders_are_not_valid(tmp_path):
    assert not GameFolder(tmp_path).is_valid
    assert not GameFolder(tmp_path / "missing").is_valid


def test_autodrive_paths(tmp_path):
    folder = GameFolder(tmp_path)

    manager = tmp_path / "modSettings" / "FS25_AutoDrive" / "routesManager"
    assert folder.routes_manager_directory == manager
    assert folder.routes_xml_path == manager / "routes.xml"
    assert folder.routes_directory == manager / "routes"
    assert folder.mods_directory == tmp_path / "mods"


def test_savegames_are_sorted_by_number_and_backup_is_skipped(tmp_path):
    folder = GameFolder(make_game_folder(tmp_path / "fs"))

    names = [path.name for path in folder.savegame_directories()]

    assert names == ["savegame1", "savegame2", "savegame10"]


def test_default_path_is_in_my_games(qapp):
    path = GameFolder.default_path()

    assert path.parts[-2:] == ("My Games", "FarmingSimulator2025")


def test_detect_finds_folder_at_default_location(tmp_path, monkeypatch):
    fake = make_game_folder(tmp_path / "FarmingSimulator2025")
    monkeypatch.setattr(GameFolder, "default_path", staticmethod(lambda: fake))

    assert GameFolder.detect().path == fake


def test_detect_returns_none_without_game_folder(tmp_path, monkeypatch):
    monkeypatch.setattr(GameFolder, "default_path", staticmethod(lambda: tmp_path / "none"))

    assert GameFolder.detect() is None
