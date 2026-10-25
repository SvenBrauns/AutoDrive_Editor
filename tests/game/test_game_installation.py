from base_game_helpers import make_installation

from autodrive_editor.game.game_installation import GameInstallation


def library_file(tmp_path, *libraries):
    entries = "".join(
        f'"{index}"\n{{\n\t\t"path"\t\t"{str(library).replace(chr(92), chr(92) * 2)}"\n}}\n'
        for index, library in enumerate(libraries)
    )
    path = tmp_path / "libraryfolders.vdf"
    path.write_text(f'"libraryfolders"\n{{\n{entries}}}\n', encoding="utf-8")
    return path


def test_install_folder_needs_executable_and_maps(tmp_path):
    assert not GameInstallation(tmp_path).is_valid
    assert GameInstallation(make_installation(tmp_path / "FS25")).is_valid


def test_steam_libraries_are_candidates(tmp_path):
    vdf = library_file(tmp_path, tmp_path / "Steam", tmp_path / "SteamLibrary")

    candidates = GameInstallation.candidate_paths(vdf)

    assert candidates[:2] == [
        tmp_path / "Steam" / "steamapps" / "common" / "Farming Simulator 25",
        tmp_path / "SteamLibrary" / "steamapps" / "common" / "Farming Simulator 25",
    ]


def test_detect_finds_the_game_in_a_second_library(tmp_path):
    second = tmp_path / "SteamLibrary"
    make_installation(second / "steamapps" / "common" / "Farming Simulator 25")
    vdf = library_file(tmp_path, tmp_path / "Steam", second)

    found = GameInstallation.detect(vdf)

    assert found.path == second / "steamapps" / "common" / "Farming Simulator 25"


def test_nothing_found_without_steam_library():
    assert GameInstallation.detect() is None
