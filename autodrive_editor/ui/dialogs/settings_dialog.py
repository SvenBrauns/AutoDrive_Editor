from PySide6.QtWidgets import QDialog, QDialogButtonBox, QVBoxLayout

from autodrive_editor.settings.app_settings import AppSettings
from autodrive_editor.ui.dialogs.folder_settings_widget import FolderSettingsWidget


class SettingsDialog(QDialog):
    """Editor settings: the FS25 user folder and install folder."""

    def __init__(self, settings: AppSettings, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Einstellungen")
        self.setMinimumWidth(560)

        self.folders = FolderSettingsWidget(settings, self)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(self.folders)
        layout.addStretch(1)
        layout.addWidget(buttons)

    def accept(self):
        self.folders.store()

        super().accept()
