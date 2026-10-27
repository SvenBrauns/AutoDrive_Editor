import tomllib

from PySide6.QtWidgets import QMessageBox, QTextBrowser

from autodrive_editor import __version__
from autodrive_editor.paths import CHANGELOG_PATH, PROJECT_ROOT
from autodrive_editor.ui.dialogs import help_dialogs
from autodrive_editor.ui.dialogs.error_dialog import create_error_box


def test_version_matches_pyproject():
    with open(PROJECT_ROOT / "pyproject.toml", "rb") as file:
        assert tomllib.load(file)["project"]["version"] == __version__


def test_about_shows_version_and_license(window):
    box = help_dialogs.create_about_box(window)

    assert f"Version {__version__}" in box.text()
    assert "GNU General Public License" in box.text()
    assert help_dialogs.REPOSITORY_URL in box.text()


def test_version_history_shows_the_changelog(window):
    dialog = help_dialogs.create_version_history_dialog(window)

    text = dialog.findChild(QTextBrowser).toPlainText()
    assert "Version history" in text
    assert "0.1.0" in text


def test_changelog_has_an_entry_for_the_current_version():
    assert f"## {__version__} – " in CHANGELOG_PATH.read_text(encoding="utf-8")


def test_missing_changelog_is_explained(window, monkeypatch, tmp_path):
    monkeypatch.setattr(help_dialogs, "CHANGELOG_PATH", tmp_path / "missing.md")

    dialog = help_dialogs.create_version_history_dialog(window)

    assert "could not be found" in dialog.findChild(QTextBrowser).toPlainText()


def test_help_menu_has_the_entries(window):
    (help_menu,) = [
        action.menu() for action in window.menuBar().actions() if action.text() == "Help"
    ]

    assert [action.text() for action in help_menu.actions() if action.text()] == [
        "Version history",
        "Open log folder",
        "About AutoDrive FS25 Editor",
    ]


def test_error_box_shows_message_details_and_log_button(window):
    box = create_error_box(window, "Traceback ... ValueError: broken")

    assert box.text() == "An unexpected error occurred."
    assert box.detailedText() == "Traceback ... ValueError: broken"
    assert "Open log folder" in [button.text() for button in box.buttons()]
    assert box.icon() == QMessageBox.Critical
