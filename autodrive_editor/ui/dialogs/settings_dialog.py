from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QSpinBox, QVBoxLayout

from autodrive_editor.settings.app_settings import AppSettings
from autodrive_editor.ui.dialogs.folder_settings_widget import FolderSettingsWidget


class SettingsDialog(QDialog):
    """Editor settings: the FS25 user folder and install folder, and the
    autosave interval."""

    MAX_AUTOSAVE_MINUTES = 60

    def __init__(self, settings: AppSettings, parent=None):
        super().__init__(parent)

        self.settings = settings

        self.setWindowTitle("Einstellungen")
        self.setMinimumWidth(560)

        self.folders = FolderSettingsWidget(settings, self)

        self.autosave_input = QSpinBox(self)
        self.autosave_input.setRange(0, self.MAX_AUTOSAVE_MINUTES)
        self.autosave_input.setSuffix(" min")
        self.autosave_input.setSpecialValueText("aus")
        self.autosave_input.setValue(settings.autosave_minutes)
        self.autosave_input.setToolTip(
            "Ungespeicherte Änderungen werden in diesem Abstand im Datenordner des Editors "
            "gesichert und nach einem Absturz beim nächsten Start angeboten."
        )

        autosave_form = QFormLayout()
        autosave_form.addRow("Automatisch sichern alle", self.autosave_input)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(self.folders)
        layout.addLayout(autosave_form)
        layout.addStretch(1)
        layout.addWidget(buttons)

    def accept(self):
        self.folders.store()
        self.settings.set_autosave_minutes(self.autosave_input.value())

        super().accept()
