import pytest
from game_folder_helpers import make_game_folder

from autodrive_editor.game.game_folder import GameFolder
from autodrive_editor.settings.app_settings import AppSettings
from autodrive_editor.ui.dialogs.settings_dialog import SettingsDialog

pytestmark = pytest.mark.usefixtures("isolated_user_data")


def test_dialog_shows_configured_folder_and_status(qapp, tmp_path):
    folder = make_game_folder(tmp_path / "fs25")
    settings = AppSettings()
    settings.set_game_folder(folder)

    dialog = SettingsDialog(settings)

    assert dialog.game_folder_input.text() == str(folder)
    assert dialog.status_label.text() == SettingsDialog.VALID_TEXT


def test_status_reports_wrong_and_empty_folders(qapp, tmp_path):
    dialog = SettingsDialog(AppSettings())

    dialog.game_folder_input.setText(str(tmp_path))
    assert dialog.status_label.text() == SettingsDialog.INVALID_TEXT

    dialog.game_folder_input.setText("")
    assert dialog.status_label.text() == SettingsDialog.EMPTY_TEXT


def test_ok_stores_the_folder(qapp, tmp_path):
    folder = make_game_folder(tmp_path / "fs25")
    settings = AppSettings()
    dialog = SettingsDialog(settings)

    dialog.game_folder_input.setText(str(folder))
    dialog.accept()

    assert AppSettings().game_folder.path == folder


def test_cancel_keeps_the_old_folder(qapp, tmp_path):
    settings = AppSettings()
    settings.set_game_folder(tmp_path / "old")
    dialog = SettingsDialog(settings)

    dialog.game_folder_input.setText(str(tmp_path / "new"))
    dialog.reject()

    assert AppSettings().game_folder.path == tmp_path / "old"


def test_detect_button_fills_in_default_folder(qapp, tmp_path, monkeypatch):
    fake = make_game_folder(tmp_path / "FarmingSimulator2025")
    monkeypatch.setattr(GameFolder, "default_path", staticmethod(lambda: fake))
    dialog = SettingsDialog(AppSettings())

    dialog._detect()

    assert dialog.game_folder_input.text() == str(fake)


def test_settings_menu_entry_exists(window, isolated_user_data):
    assert window.actions.settings_action.text() == "Einstellungen…"
    assert "user_data" in window.settings.settings_path.parent.name
