from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QSpinBox,
    QVBoxLayout,
)

from autodrive_editor.i18n import LANGUAGES, tr
from autodrive_editor.settings.app_settings import AppSettings
from autodrive_editor.ui.dialogs.folder_settings_widget import FolderSettingsWidget


class SettingsDialog(QDialog):
    """Editor settings: the FS25 user folder and install folder, the
    autosave interval and the language."""

    MAX_AUTOSAVE_MINUTES = 60

    def __init__(self, settings: AppSettings, parent=None):
        super().__init__(parent)

        self.settings = settings

        self.setWindowTitle(tr("Settings"))
        self.setMinimumWidth(560)

        self.folders = FolderSettingsWidget(settings, self)

        self.autosave_input = QSpinBox(self)
        self.autosave_input.setRange(0, self.MAX_AUTOSAVE_MINUTES)
        self.autosave_input.setSuffix(" min")
        self.autosave_input.setSpecialValueText(tr("off"))
        self.autosave_input.setValue(settings.autosave_minutes)
        self.autosave_input.setToolTip(
            tr(
                "Unsaved changes are backed up at this interval in the editor's data folder "
                "and offered on the next start after a crash."
            )
        )

        self.language_input = QComboBox(self)

        for language, name in LANGUAGES.items():
            self.language_input.addItem(name, language)

        self.language_input.setCurrentIndex(self.language_input.findData(settings.language))

        form = QFormLayout()
        form.addRow(tr("Autosave every"), self.autosave_input)
        form.addRow(tr("Language:"), self.language_input)
        form.addRow("", QLabel(tr("Takes effect after a restart."), self))

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(self.folders)
        layout.addLayout(form)
        layout.addStretch(1)
        layout.addWidget(buttons)

    def accept(self):
        self.folders.store()
        self.settings.set_autosave_minutes(self.autosave_input.value())

        # Stored only when changed, so the editor keeps following the
        # Windows language until a language is chosen.
        language = self.language_input.currentData()

        if language != self.settings.language:
            self.settings.set_language(language)

        super().accept()
