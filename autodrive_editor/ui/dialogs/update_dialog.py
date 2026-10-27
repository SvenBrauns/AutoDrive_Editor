"""Tells the user about a newer version and links to its download page."""

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QMessageBox

from autodrive_editor import __version__
from autodrive_editor.i18n import tr
from autodrive_editor.ui.dialogs.messages import APP_TITLE
from autodrive_editor.updates import Release


def create_update_box(parent, release: Release) -> QMessageBox:
    box = QMessageBox(parent)
    box.setWindowTitle(APP_TITLE)
    box.setIcon(QMessageBox.Icon.Information)
    box.setText(
        tr(
            "Version {new} is available. You have version {current}.",
            new=release.version,
            current=__version__,
        )
    )
    box.setInformativeText(
        tr("Download the zip and replace the old program folder with it. Your settings are kept.")
    )

    if release.notes:
        box.setDetailedText(release.notes)

    box.download_button = box.addButton(tr("Open download page"), QMessageBox.ButtonRole.AcceptRole)
    box.addButton(tr("Later"), QMessageBox.ButtonRole.RejectRole)
    box.setDefaultButton(box.download_button)

    return box


def show_update(parent, release: Release):
    box = create_update_box(parent, release)
    box.exec()

    if box.clickedButton() is box.download_button:
        QDesktopServices.openUrl(QUrl(release.url))
