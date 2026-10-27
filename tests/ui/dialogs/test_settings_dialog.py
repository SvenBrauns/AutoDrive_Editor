import pytest
from base_game_helpers import make_installation
from game_folder_helpers import make_game_folder
from PySide6.QtGui import QAction, QKeySequence

from autodrive_editor.game.game_folder import GameFolder
from autodrive_editor.game.game_installation import GameInstallation
from autodrive_editor.settings import app_settings
from autodrive_editor.settings.app_settings import AppSettings
from autodrive_editor.ui.actions.shortcuts import ShortcutRegistry
from autodrive_editor.ui.dialogs.folder_settings_widget import FolderSettingsWidget
from autodrive_editor.ui.dialogs.settings_dialog import SettingsDialog

pytestmark = pytest.mark.usefixtures("isolated_user_data")


def test_dialog_shows_configured_folder_and_status(qapp, tmp_path):
    folder = make_game_folder(tmp_path / "fs25")
    settings = AppSettings()
    settings.set_game_folder(folder)

    dialog = SettingsDialog(settings, ShortcutRegistry())

    assert dialog.folders.game_folder_input.text() == str(folder)
    assert dialog.folders.status_label.text() == FolderSettingsWidget.VALID_TEXT


def test_status_reports_wrong_and_empty_folders(qapp, tmp_path):
    dialog = SettingsDialog(AppSettings(), ShortcutRegistry())

    dialog.folders.game_folder_input.setText(str(tmp_path))
    assert dialog.folders.status_label.text() == FolderSettingsWidget.INVALID_TEXT

    dialog.folders.game_folder_input.setText("")
    assert dialog.folders.status_label.text() == FolderSettingsWidget.EMPTY_TEXT


def test_ok_stores_the_folder(qapp, tmp_path):
    folder = make_game_folder(tmp_path / "fs25")
    settings = AppSettings()
    dialog = SettingsDialog(settings, ShortcutRegistry())

    dialog.folders.game_folder_input.setText(str(folder))
    dialog.accept()

    assert AppSettings().game_folder.path == folder


def test_cancel_keeps_the_old_folder(qapp, tmp_path):
    settings = AppSettings()
    settings.set_game_folder(tmp_path / "old")
    dialog = SettingsDialog(settings, ShortcutRegistry())

    dialog.folders.game_folder_input.setText(str(tmp_path / "new"))
    dialog.reject()

    assert AppSettings().game_folder.path == tmp_path / "old"


def test_detect_button_fills_in_default_folder(qapp, tmp_path, monkeypatch):
    fake = make_game_folder(tmp_path / "FarmingSimulator2025")
    monkeypatch.setattr(GameFolder, "default_path", staticmethod(lambda: fake))
    dialog = SettingsDialog(AppSettings(), ShortcutRegistry())

    dialog.folders._detect()

    assert dialog.folders.game_folder_input.text() == str(fake)


def test_settings_menu_entry_exists(window, isolated_user_data):
    assert window.actions.settings_action.text() == "Settings…"
    assert "user_data" in window.settings.settings_path.parent.name


def test_install_folder_is_shown_checked_and_stored(qapp, tmp_path):
    install = make_installation(tmp_path / "FS25")
    settings = AppSettings()
    dialog = SettingsDialog(settings, ShortcutRegistry())
    assert dialog.folders.install_status_label.text() == FolderSettingsWidget.EMPTY_TEXT

    dialog.folders.install_folder_input.setText(str(tmp_path))
    assert dialog.folders.install_status_label.text() == FolderSettingsWidget.INSTALL_INVALID_TEXT

    dialog.folders.install_folder_input.setText(str(install))
    assert dialog.folders.install_status_label.text() == FolderSettingsWidget.INSTALL_VALID_TEXT

    dialog.accept()
    assert AppSettings().install_folder.path == install


def test_detect_install_button_fills_in_the_folder(qapp, tmp_path, monkeypatch):
    install = make_installation(tmp_path / "FS25")
    monkeypatch.setattr(
        GameInstallation, "detect", classmethod(lambda cls: GameInstallation(install))
    )
    dialog = SettingsDialog(AppSettings(), ShortcutRegistry())

    dialog.folders._detect_install()

    assert dialog.folders.install_folder_input.text() == str(install)


def test_autosave_interval_is_shown_and_stored(qapp):
    settings = AppSettings()
    dialog = SettingsDialog(settings, ShortcutRegistry())
    assert dialog.autosave_input.value() == AppSettings.DEFAULT_AUTOSAVE_MINUTES

    dialog.autosave_input.setValue(0)
    dialog.accept()

    assert settings.autosave_minutes == 0
    assert dialog.autosave_input.text() == "off"


def test_language_is_shown_and_stored(qapp):
    settings = AppSettings()
    settings.set_language("en")
    dialog = SettingsDialog(settings, ShortcutRegistry())
    assert dialog.language_input.currentText() == "English"

    dialog.language_input.setCurrentIndex(dialog.language_input.findData("de"))
    dialog.accept()

    assert AppSettings().language == "de"


def test_unchanged_language_keeps_following_windows(qapp, monkeypatch):
    monkeypatch.setattr(app_settings, "system_language", lambda: "de")
    SettingsDialog(AppSettings(), ShortcutRegistry()).accept()

    monkeypatch.setattr(app_settings, "system_language", lambda: "en")

    assert AppSettings().language == "en"


def test_theme_is_shown_and_stored(qapp):
    settings = AppSettings()
    dialog = SettingsDialog(settings, ShortcutRegistry())
    assert dialog.theme_input.currentText() == "Like Windows"

    dialog.theme_input.setCurrentIndex(dialog.theme_input.findData("dark"))
    dialog.accept()

    assert AppSettings().theme == "dark"


def test_changed_shortcuts_are_stored(qapp):
    action = QAction("Save")
    registry = ShortcutRegistry()
    registry.add("save", "File", action)
    dialog = SettingsDialog(AppSettings(), registry)

    dialog.shortcuts.edits["save"].setKeySequence(QKeySequence("F2"))
    dialog.accept()

    assert AppSettings().shortcuts == {"save": ["F2"]}


def test_update_check_is_shown_and_stored(qapp):
    settings = AppSettings()
    dialog = SettingsDialog(settings, ShortcutRegistry())
    assert not dialog.check_updates_input.isChecked()

    dialog.check_updates_input.setChecked(True)
    dialog.accept()

    assert AppSettings().check_updates
