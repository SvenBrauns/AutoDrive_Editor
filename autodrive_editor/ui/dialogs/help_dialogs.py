"""The Help menu: the manual, about the editor, version history and the log folder."""

import re

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QIcon, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QMessageBox, QTextBrowser, QVBoxLayout

from autodrive_editor import __version__
from autodrive_editor.i18n import current_language, tr
from autodrive_editor.paths import APP_ICON_PATH, CHANGELOG_PATH, MANUAL_PATHS, log_directory
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


def create_manual_dialog(parent) -> QDialog:
    """The manual in the editor's language, shown as formatted text. Links inside the manual
    and to the other language work; web links open in the browser."""

    dialog = QDialog(parent)
    dialog.setObjectName("manual")
    dialog.setWindowTitle(tr("Manual"))
    dialog.resize(760, 680)

    browser = QTextBrowser(dialog)
    browser.setOpenLinks(False)
    browser.anchorClicked.connect(lambda url: _follow_manual_link(browser, url))
    _load_manual(browser, MANUAL_PATHS[current_language()].name)

    buttons = QDialogButtonBox(QDialogButtonBox.Close, dialog)
    buttons.rejected.connect(dialog.reject)

    layout = QVBoxLayout(dialog)
    layout.addWidget(browser)
    layout.addWidget(buttons)

    return dialog


def show_manual(parent):
    """Shows the manual beside the editor; a second call brings the open one to the front."""

    dialog = parent.findChild(QDialog, "manual") or create_manual_dialog(parent)
    dialog.show()
    dialog.raise_()
    dialog.activateWindow()


def heading_anchor(heading: str) -> str:
    """The link target GitHub gives a heading: lower case, punctuation dropped, spaces to -."""

    return re.sub(r"[^\w\- ]", "", heading.strip().lower()).replace(" ", "-")


def _load_manual(browser: QTextBrowser, file_name: str):
    paths = {path.name: path for path in MANUAL_PATHS.values()}

    try:
        browser.setMarkdown(paths[file_name].read_text(encoding="utf-8"))
    except OSError:
        browser.setPlainText(tr("The manual could not be found."))
        return

    # Qt gives headings no link targets; add them so the table of contents works.
    block = browser.document().begin()

    while block.isValid():
        if block.blockFormat().headingLevel():
            anchor = QTextCharFormat()
            anchor.setAnchor(True)
            anchor.setAnchorNames([heading_anchor(block.text())])
            cursor = QTextCursor(block)
            cursor.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
            cursor.mergeCharFormat(anchor)

        block = block.next()


def _follow_manual_link(browser: QTextBrowser, url: QUrl):
    if url.scheme() in ("http", "https"):
        QDesktopServices.openUrl(url)

    elif url.path() in {path.name for path in MANUAL_PATHS.values()}:
        _load_manual(browser, url.path())

    elif not url.path() and url.fragment():
        browser.scrollToAnchor(url.fragment())


def open_log_folder():
    folder = log_directory()
    folder.mkdir(parents=True, exist_ok=True)
    QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))
