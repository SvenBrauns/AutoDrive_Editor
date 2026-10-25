import pytest
from game_folder_helpers import make_game_folder

from autodrive_editor.game.game_folder import GameFolder
from autodrive_editor.settings.app_settings import AppSettings

pytestmark = pytest.mark.usefixtures("isolated_user_data")


def test_settings_live_in_the_user_data_folder(isolated_user_data):
    settings = AppSettings()

    assert settings.settings_path == isolated_user_data / "settings.ini"


def test_game_folder_is_kept_between_sessions(tmp_path):
    AppSettings().set_game_folder(tmp_path / "fs25")

    assert AppSettings().game_folder.path == tmp_path / "fs25"


def test_game_folder_can_be_cleared(tmp_path):
    settings = AppSettings()
    settings.set_game_folder(tmp_path)

    settings.set_game_folder(None)

    assert AppSettings().game_folder is None


def test_first_start_stores_detected_game_folder(tmp_path, monkeypatch):
    fake = make_game_folder(tmp_path / "FarmingSimulator2025")
    monkeypatch.setattr(GameFolder, "default_path", staticmethod(lambda: fake))

    folder = AppSettings().ensure_game_folder()

    assert folder.path == fake
    assert AppSettings().game_folder.path == fake


def test_configured_game_folder_is_not_replaced_by_detection(tmp_path, monkeypatch):
    fake = make_game_folder(tmp_path / "FarmingSimulator2025")
    monkeypatch.setattr(GameFolder, "default_path", staticmethod(lambda: fake))
    settings = AppSettings()
    settings.set_game_folder(tmp_path / "my_own_choice")

    assert settings.ensure_game_folder().path == tmp_path / "my_own_choice"


def test_without_game_folder_nothing_is_stored(tmp_path, monkeypatch):
    monkeypatch.setattr(GameFolder, "default_path", staticmethod(lambda: tmp_path / "none"))

    assert AppSettings().ensure_game_folder() is None
