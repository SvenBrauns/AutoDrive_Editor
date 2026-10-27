from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from autodrive_editor.i18n import LANGUAGES, tr
from autodrive_editor.settings.app_settings import AppSettings
from autodrive_editor.ui.actions.shortcuts import ShortcutRegistry
from autodrive_editor.ui.dialogs.folder_settings_widget import FolderSettingsWidget
from autodrive_editor.ui.dialogs.shortcuts_widget import ShortcutsWidget

THEME_NAMES = {"system": tr("Like Windows"), "light": tr("Light"), "dark": tr("Dark")}


class SettingsDialog(QDialog):
    """Editor settings: the FS25 user folder and install folder, the
    autosave interval, the language, the theme and the keyboard shortcuts."""

    MAX_AUTOSAVE_MINUTES = 60

    def __init__(self, settings: AppSettings, shortcuts: ShortcutRegistry, parent=None):
        super().__init__(parent)

        self.settings = settings

        self.setWindowTitle(tr("Settings"))
        self.setMinimumWidth(560)

        general = QWidget(self)
        self.folders = FolderSettingsWidget(settings, general)

        self.autosave_input = QSpinBox(general)
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

        self.language_input = QComboBox(general)

        for language, name in LANGUAGES.items():
            self.language_input.addItem(name, language)

        self.language_input.setCurrentIndex(self.language_input.findData(settings.language))

        self.theme_input = QComboBox(general)

        for theme, name in THEME_NAMES.items():
            self.theme_input.addItem(name, theme)

        self.theme_input.setCurrentIndex(self.theme_input.findData(settings.theme))

        form = QFormLayout()
        form.addRow(tr("Autosave every"), self.autosave_input)
        form.addRow(tr("Language:"), self.language_input)
        form.addRow("", QLabel(tr("Takes effect after a restart."), general))
        form.addRow(tr("Theme:"), self.theme_input)

        general_layout = QVBoxLayout(general)
        general_layout.addWidget(self.folders)
        general_layout.addLayout(form)
        general_layout.addStretch(1)

        self.shortcuts = ShortcutsWidget(shortcuts, self)

        self.tabs = QTabWidget(self)
        self.tabs.addTab(general, tr("General"))
        self.tabs.addTab(self.shortcuts, tr("Shortcuts"))

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(self.tabs)
        layout.addWidget(buttons)

    def accept(self):
        self.folders.store()
        self.settings.set_autosave_minutes(self.autosave_input.value())
        self.settings.set_theme(self.theme_input.currentData())
        self.settings.set_shortcuts(self.shortcuts.changed_keys())

        # Stored only when changed, so the editor keeps following the
        # Windows language until a language is chosen.
        language = self.language_input.currentData()

        if language != self.settings.language:
            self.settings.set_language(language)

        super().accept()
