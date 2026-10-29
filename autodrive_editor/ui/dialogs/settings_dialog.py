from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from autodrive_editor.editing.route_finder import Vehicle
from autodrive_editor.i18n import LANGUAGES, tr
from autodrive_editor.settings.app_settings import AppSettings
from autodrive_editor.ui.actions.shortcuts import ShortcutRegistry
from autodrive_editor.ui.dialogs.folder_settings_widget import FolderSettingsWidget
from autodrive_editor.ui.dialogs.shortcuts_widget import ShortcutsWidget

THEME_NAMES = {"system": tr("Like Windows"), "light": tr("Light"), "dark": tr("Dark")}
UPDATE_CHECK_TEXT = tr("Check for a new version at startup (contacts github.com)")


class SettingsDialog(QDialog):
    """Editor settings: the FS25 user folder and install folder, the
    autosave interval, the language, the theme, the vehicle size for the
    route finder and the keyboard shortcuts."""

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

        self.check_updates_input = QCheckBox(UPDATE_CHECK_TEXT, general)
        self.check_updates_input.setChecked(settings.check_updates)

        self.reopen_last_input = QCheckBox(tr("Open the last opened file at startup"), general)
        self.reopen_last_input.setChecked(settings.reopen_last)

        form = QFormLayout()
        form.addRow(tr("Autosave every"), self.autosave_input)
        form.addRow(tr("Language:"), self.language_input)
        form.addRow("", QLabel(tr("Takes effect after a restart."), general))
        form.addRow(tr("Theme:"), self.theme_input)
        form.addRow("", self.check_updates_input)
        form.addRow("", self.reopen_last_input)

        general_layout = QVBoxLayout(general)
        general_layout.addWidget(self.folders)
        general_layout.addLayout(form)
        general_layout.addStretch(1)

        self.shortcuts = ShortcutsWidget(shortcuts, self)

        self.tabs = QTabWidget(self)
        self.tabs.addTab(general, tr("General"))
        self.tabs.addTab(self._create_route_tab(), tr("Route finder"))
        self.tabs.addTab(self.shortcuts, tr("Shortcuts"))

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(self.tabs)
        layout.addWidget(buttons)

    def _create_route_tab(self) -> QWidget:
        tab = QWidget(self)
        vehicle = self.settings.vehicle

        def metres_input(value: float, minimum: float, maximum: float) -> QDoubleSpinBox:
            spin_box = QDoubleSpinBox(tab)
            spin_box.setRange(minimum, maximum)
            spin_box.setDecimals(1)
            spin_box.setSingleStep(0.5)
            spin_box.setSuffix(" m")
            spin_box.setValue(value)

            return spin_box

        self.turning_radius_input = metres_input(vehicle.turning_radius, 3.0, 50.0)
        self.vehicle_width_input = metres_input(vehicle.width, 1.0, 10.0)
        self.safety_margin_input = metres_input(vehicle.margin, 0.1, 5.0)

        note = QLabel(
            tr(
                "Find route plans for a vehicle of this size: it turns no tighter than the "
                "turning radius and keeps half its width plus the safety margin away from "
                "buildings, fences and trees."
            ),
            tab,
        )
        note.setWordWrap(True)

        form = QFormLayout(tab)
        form.addRow(note)
        form.addRow(tr("Minimum turning radius:"), self.turning_radius_input)
        form.addRow(tr("Vehicle width:"), self.vehicle_width_input)
        form.addRow(tr("Safety margin:"), self.safety_margin_input)

        return tab

    def accept(self):
        self.folders.store()
        self.settings.set_vehicle(
            Vehicle(
                self.turning_radius_input.value(),
                self.vehicle_width_input.value(),
                self.safety_margin_input.value(),
            )
        )
        self.settings.set_autosave_minutes(self.autosave_input.value())
        self.settings.set_theme(self.theme_input.currentData())
        self.settings.set_check_updates(self.check_updates_input.isChecked())
        self.settings.set_reopen_last(self.reopen_last_input.isChecked())
        self.settings.set_shortcuts(self.shortcuts.changed_keys())

        # Stored only when changed, so the editor keeps following the
        # Windows language until a language is chosen.
        language = self.language_input.currentData()

        if language != self.settings.language:
            self.settings.set_language(language)

        super().accept()
