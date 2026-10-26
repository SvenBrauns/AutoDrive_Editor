"""Shown on the first start: checks the detected FS25 folders and offers
to import the maps right away, so loaded routes find their map."""

from PySide6.QtWidgets import QCheckBox, QDialog, QDialogButtonBox, QLabel, QVBoxLayout

from autodrive_editor.i18n import tr
from autodrive_editor.settings.app_settings import AppSettings
from autodrive_editor.ui.dialogs.folder_settings_widget import FolderSettingsWidget


class FirstStartDialog(QDialog):
    INTRO_TEXT = tr(
        "Welcome to the AutoDrive Editor for FS25.\n\n"
        "The editor needs two folders: the FS25 user folder with routes, savegames "
        "and mods, and the installation folder with the base game maps. Both were "
        "detected automatically where possible. Everything can be changed later under "
        "File → Settings."
    )

    SCAN_TEXT = tr("Then scan maps (base game maps and map mods in the mods folder)")

    def __init__(self, settings: AppSettings, parent=None):
        super().__init__(parent)

        self.setWindowTitle(tr("Setup"))
        self.setMinimumWidth(680)

        intro = QLabel(self.INTRO_TEXT, self)
        intro.setWordWrap(True)

        self.folders = FolderSettingsWidget(settings, self)

        self.scan_check_box = QCheckBox(self.SCAN_TEXT, self)
        self.scan_check_box.setChecked(True)

        buttons = QDialogButtonBox(self)
        start_button = buttons.addButton(tr("Done"), QDialogButtonBox.ButtonRole.AcceptRole)
        start_button.setDefault(True)
        buttons.addButton(tr("Skip"), QDialogButtonBox.ButtonRole.RejectRole)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(intro)
        layout.addWidget(self.folders)
        layout.addWidget(self.scan_check_box)
        layout.addStretch(1)
        layout.addWidget(buttons)

    @property
    def scan_requested(self) -> bool:
        return self.result() == QDialog.DialogCode.Accepted and self.scan_check_box.isChecked()

    def accept(self):
        self.folders.store()

        super().accept()
