"""Shown on the first start: checks the detected FS25 folders and offers
to import the maps right away, so loaded routes find their map."""

from PySide6.QtWidgets import QCheckBox, QDialog, QDialogButtonBox, QLabel, QVBoxLayout

from autodrive_editor.settings.app_settings import AppSettings
from autodrive_editor.ui.dialogs.folder_settings_widget import FolderSettingsWidget


class FirstStartDialog(QDialog):
    INTRO_TEXT = (
        "Willkommen im AutoDrive Editor für LS25.\n\n"
        "Der Editor braucht zwei Ordner: den LS25-Benutzerordner mit Routen, Savegames "
        "und Mods sowie den Installationsordner mit den Grundspiel-Karten. Beide wurden, "
        "wenn möglich, automatisch erkannt. Alles lässt sich später unter "
        "Datei → Einstellungen ändern."
    )

    SCAN_TEXT = "Danach Karten scannen (Grundspiel-Karten und Kartenmods im Mods-Ordner)"

    def __init__(self, settings: AppSettings, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Einrichtung")
        self.setMinimumWidth(680)

        intro = QLabel(self.INTRO_TEXT, self)
        intro.setWordWrap(True)

        self.folders = FolderSettingsWidget(settings, self)

        self.scan_check_box = QCheckBox(self.SCAN_TEXT, self)
        self.scan_check_box.setChecked(True)

        buttons = QDialogButtonBox(self)
        start_button = buttons.addButton("Fertig", QDialogButtonBox.ButtonRole.AcceptRole)
        start_button.setDefault(True)
        buttons.addButton("Überspringen", QDialogButtonBox.ButtonRole.RejectRole)
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
