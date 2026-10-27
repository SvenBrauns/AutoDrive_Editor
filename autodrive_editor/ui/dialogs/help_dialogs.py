"""The Help menu: about the editor, version history and the log folder."""

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QIcon
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QMessageBox, QTextBrowser, QVBoxLayout

from autodrive_editor import __version__
from autodrive_editor.i18n import tr
from autodrive_editor.paths import APP_ICON_PATH, CHANGELOG_PATH, log_directory
from autodrive_editor.ui.dialogs.messages import APP_TITLE

REPOSITORY_URL = "https://github.com/SvenBrauns/AutoDrive_Editor"


def create_about_box(parent) -> QMessageBox:
    box = QMessageBox(parent)
    box.setWindowTitle(tr("About AutoDrive FS25 Editor"))
    box.setIconPixmap(QIcon(str(APP_ICON_PATH)).pixmap(64, 64))
    box.setTextFormat(Qt.RichText)
    box.setText(
        f"<h3>{APP_TITLE}</h3>"
        f"<p>{tr('Version {version}', version=__version__)}</p>"
        f"<p>{tr('Desktop editor for AutoDrive route networks in Farming Simulator 25.')}</p>"
        f"<p>{tr('License: GNU General Public License v3.0 or later.')}<br>"
        f"{tr('Contains PySide6/Qt (LGPLv3) and Pillow.')}</p>"
        f'<p><a href="{REPOSITORY_URL}">{REPOSITORY_URL.removeprefix("https://")}</a></p>'
        f"<p>{tr('This project has no connection to GIANTS Software.')}</p>"
    )
    return box


def show_about(parent):
    create_about_box(parent).exec()


def create_version_history_dialog(parent) -> QDialog:
    """CHANGELOG.md, shown as formatted text."""

    dialog = QDialog(parent)
    dialog.setWindowTitle(tr("Version history"))
    dialog.resize(640, 520)

    browser = QTextBrowser(dialog)
    browser.setOpenExternalLinks(True)

    try:
        browser.setMarkdown(CHANGELOG_PATH.read_text(encoding="utf-8"))
    except OSError:
        browser.setPlainText(tr("The version history could not be found."))

    buttons = QDialogButtonBox(QDialogButtonBox.Close, dialog)
    buttons.rejected.connect(dialog.reject)

    layout = QVBoxLayout(dialog)
    layout.addWidget(browser)
    layout.addWidget(buttons)

    return dialog


def show_version_history(parent):
    create_version_history_dialog(parent).exec()


def open_log_folder():
    folder = log_directory()
    folder.mkdir(parents=True, exist_ok=True)
    QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))
