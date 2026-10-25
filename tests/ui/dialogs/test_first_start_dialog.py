import pytest
from base_game_helpers import make_installation
from game_folder_helpers import make_game_folder

from autodrive_editor.settings.app_settings import AppSettings
from autodrive_editor.ui.dialogs.first_start_dialog import FirstStartDialog
from autodrive_editor.ui.dialogs.folder_settings_widget import FolderSettingsWidget

pytestmark = pytest.mark.usefixtures("isolated_user_data")


def test_dialog_shows_detected_folders(qapp, tmp_path):
    settings = AppSettings()
    settings.set_game_folder(make_game_folder(tmp_path / "fs25"))
    settings.set_install_folder(make_installation(tmp_path / "install"))

    dialog = FirstStartDialog(settings)

    assert dialog.folders.status_label.text() == FolderSettingsWidget.VALID_TEXT
    assert dialog.folders.install_status_label.text() == FolderSettingsWidget.INSTALL_VALID_TEXT
    assert dialog.scan_check_box.isChecked()


def test_finish_stores_folders_and_requests_scan(qapp, tmp_path):
    folder = make_game_folder(tmp_path / "fs25")
    dialog = FirstStartDialog(AppSettings())

    dialog.folders.game_folder_input.setText(str(folder))
    dialog.accept()

    assert AppSettings().game_folder.path == folder
    assert dialog.scan_requested


def test_scan_can_be_turned_off(qapp):
    dialog = FirstStartDialog(AppSettings())

    dialog.scan_check_box.setChecked(False)
    dialog.accept()

    assert not dialog.scan_requested


def test_skip_stores_nothing_and_does_not_scan(qapp, tmp_path):
    dialog = FirstStartDialog(AppSettings())

    dialog.folders.game_folder_input.setText(str(tmp_path))
    dialog.reject()

    assert AppSettings().game_folder is None
    assert not dialog.scan_requested
