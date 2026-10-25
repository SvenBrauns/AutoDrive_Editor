from pathlib import Path

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from autodrive_editor.game.game_folder import GameFolder
from autodrive_editor.settings.app_settings import AppSettings


class SettingsDialog(QDialog):
    """Editor settings. For now only the FS25 game folder, which is used
    to find AutoDrive routes, savegames and map mods."""

    VALID_TEXT = "✔ FS25-Ordner gefunden"
    INVALID_TEXT = "✖ Kein FS25-Benutzerordner (game.xml fehlt)"
    EMPTY_TEXT = "Kein Ordner gewählt"

    def __init__(self, settings: AppSettings, parent=None):
        super().__init__(parent)

        self.settings = settings

        self.setWindowTitle("Einstellungen")
        self.setMinimumWidth(560)

        game_group = QGroupBox("Spielordner", self)

        self.game_folder_input = QLineEdit(game_group)
        self.game_folder_input.setPlaceholderText(str(GameFolder.default_path()))
        self.game_folder_input.textChanged.connect(self._update_status)

        browse_button = QPushButton("Durchsuchen…", game_group)
        browse_button.clicked.connect(self._browse)

        detect_button = QPushButton("Automatisch erkennen", game_group)
        detect_button.clicked.connect(self._detect)

        folder_row = QHBoxLayout()
        folder_row.addWidget(self.game_folder_input, 1)
        folder_row.addWidget(browse_button)
        folder_row.addWidget(detect_button)

        self.status_label = QLabel(game_group)

        hint = QLabel(
            "Der FS25-Benutzerordner enthält die Savegames, den Mods-Ordner und die "
            "AutoDrive-Routen (modSettings\\FS25_AutoDrive\\routesManager).",
            game_group,
        )
        hint.setWordWrap(True)

        form = QFormLayout(game_group)
        form.addRow("FS25-Ordner:", folder_row)
        form.addRow("", self.status_label)
        form.addRow(hint)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(game_group)
        layout.addStretch(1)
        layout.addWidget(buttons)

        current = settings.game_folder
        self.game_folder_input.setText(str(current.path) if current else "")
        self._update_status()

    @property
    def chosen_folder(self) -> GameFolder | None:
        text = self.game_folder_input.text().strip()

        return GameFolder(text) if text else None

    def accept(self):
        folder = self.chosen_folder
        self.settings.set_game_folder(folder.path if folder else None)

        super().accept()

    def _browse(self):
        start = self.game_folder_input.text().strip() or str(GameFolder.default_path().parent)

        chosen = QFileDialog.getExistingDirectory(self, "FS25-Benutzerordner wählen", start)

        if chosen:
            self.game_folder_input.setText(str(Path(chosen)))

    def _detect(self):
        detected = GameFolder.detect()

        if detected is not None:
            self.game_folder_input.setText(str(detected.path))
        else:
            self.status_label.setText(
                f"✖ Nicht gefunden unter {GameFolder.default_path()}. "
                "Bitte über „Durchsuchen…“ wählen."
            )

    def _update_status(self):
        folder = self.chosen_folder

        if folder is None:
            self.status_label.setText(self.EMPTY_TEXT)
        elif folder.is_valid:
            self.status_label.setText(self.VALID_TEXT)
        else:
            self.status_label.setText(self.INVALID_TEXT)
