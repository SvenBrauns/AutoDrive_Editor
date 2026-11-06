import re
import tomllib

import pytest
from PySide6.QtWidgets import QMessageBox, QTextBrowser

from autodrive_editor import __version__
from autodrive_editor.paths import CHANGELOG_PATH, MANUAL_PATHS, PROJECT_ROOT
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
    headings = [
        line.split(" – ")[0] for line in CHANGELOG_PATH.read_text(encoding="utf-8").splitlines()
    ]
    assert f"## {__version__}" in headings


def test_missing_changelog_is_explained(window, monkeypatch, tmp_path):
    monkeypatch.setattr(help_dialogs, "CHANGELOG_PATH", tmp_path / "missing.md")

    dialog = help_dialogs.create_version_history_dialog(window)

    assert "could not be found" in dialog.findChild(QTextBrowser).toPlainText()


def test_help_menu_has_the_entries(window):
    (help_menu,) = [
        action.menu() for action in window.menuBar().actions() if action.text() == "Help"
    ]

    assert [action.text() for action in help_menu.actions() if action.text()] == [
        "Manual",
        "Version history",
        "Check for updates",
        "Debug info",
        "Debug log",
        "Open log folder",
        "About AutoDrive FS25 Editor",
    ]


@pytest.mark.parametrize(("language", "title"), [("en", "Manual"), ("de", "Anleitung")])
def test_manual_is_shown_in_the_editor_language(window, monkeypatch, language, title):
    monkeypatch.setattr(help_dialogs, "current_language", lambda: language)

    dialog = help_dialogs.create_manual_dialog(window)

    assert (
        dialog.findChild(QTextBrowser).toPlainText().startswith(f"AutoDrive FS25 Editor – {title}")
    )


@pytest.mark.parametrize("path", MANUAL_PATHS.values(), ids=lambda path: path.name)
def test_every_link_of_the_manual_contents_has_a_heading(path):
    text = path.read_text(encoding="utf-8")
    anchors = {help_dialogs.heading_anchor(h) for h in re.findall(r"^#+ (.+)$", text, re.M)}

    assert set(re.findall(r"\]\(#([^)]+)\)", text)) <= anchors


def test_error_box_shows_message_details_and_log_button(window):
    box = create_error_box(window, "Traceback ... ValueError: broken")

    assert box.text() == "An unexpected error occurred."
    assert box.detailedText() == "Traceback ... ValueError: broken"
    assert "Open log folder" in [button.text() for button in box.buttons()]
    assert box.icon() == QMessageBox.Critical
