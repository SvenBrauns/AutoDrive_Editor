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
from autodrive_editor.game.game_installation import GAME_EXECUTABLE, GameInstallation
from autodrive_editor.settings.app_settings import AppSettings


class SettingsDialog(QDialog):
    """Editor settings: the FS25 user folder (AutoDrive routes, savegames,
    map mods) and the FS25 install folder (base game maps)."""

    VALID_TEXT = "✔ FS25-Ordner gefunden"
    INVALID_TEXT = "✖ Kein FS25-Benutzerordner (game.xml fehlt)"
    EMPTY_TEXT = "Kein Ordner gewählt"

    INSTALL_VALID_TEXT = "✔ FS25-Installation gefunden"
    INSTALL_INVALID_TEXT = f"✖ Keine FS25-Installation ({GAME_EXECUTABLE} oder data\\maps fehlt)"

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

        install_group = self._create_install_group()

        layout = QVBoxLayout(self)
        layout.addWidget(game_group)
        layout.addWidget(install_group)
        layout.addStretch(1)
        layout.addWidget(buttons)

        current = settings.game_folder
        self.game_folder_input.setText(str(current.path) if current else "")
        self._update_status()

        installation = settings.install_folder
        self.install_folder_input.setText(str(installation.path) if installation else "")
        self._update_install_status()

    def _create_install_group(self) -> QGroupBox:
        group = QGroupBox("Installationsordner", self)

        self.install_folder_input = QLineEdit(group)
        self.install_folder_input.textChanged.connect(self._update_install_status)

        browse_button = QPushButton("Durchsuchen…", group)
        browse_button.clicked.connect(self._browse_install)

        detect_button = QPushButton("Automatisch erkennen", group)
        detect_button.clicked.connect(self._detect_install)

        folder_row = QHBoxLayout()
        folder_row.addWidget(self.install_folder_input, 1)
        folder_row.addWidget(browse_button)
        folder_row.addWidget(detect_button)

        self.install_status_label = QLabel(group)

        hint = QLabel(
            "Der Ordner, in dem LS25 installiert ist (bei Steam z. B. "
            "steamapps\\common\\Farming Simulator 25). Er enthält die Grundspiel-Karten "
            "Riverbend Springs, Zielonka und Hutan Pantai.",
            group,
        )
        hint.setWordWrap(True)

        form = QFormLayout(group)
        form.addRow("LS25-Installation:", folder_row)
        form.addRow("", self.install_status_label)
        form.addRow(hint)

        return group

    @property
    def chosen_folder(self) -> GameFolder | None:
        text = self.game_folder_input.text().strip()

        return GameFolder(text) if text else None

    @property
    def chosen_installation(self) -> GameInstallation | None:
        text = self.install_folder_input.text().strip()

        return GameInstallation(text) if text else None

    def accept(self):
        folder = self.chosen_folder
        self.settings.set_game_folder(folder.path if folder else None)

        installation = self.chosen_installation
        self.settings.set_install_folder(installation.path if installation else None)

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

    def _browse_install(self):
        start = self.install_folder_input.text().strip()

        chosen = QFileDialog.getExistingDirectory(self, "LS25-Installationsordner wählen", start)

        if chosen:
            self.install_folder_input.setText(str(Path(chosen)))

    def _detect_install(self):
        detected = GameInstallation.detect()

        if detected is not None:
            self.install_folder_input.setText(str(detected.path))
        else:
            self.install_status_label.setText("✖ Nicht gefunden. Bitte über „Durchsuchen…“ wählen.")

    def _update_install_status(self):
        installation = self.chosen_installation

        if installation is None:
            self.install_status_label.setText(self.EMPTY_TEXT)
        elif installation.is_valid:
            self.install_status_label.setText(self.INSTALL_VALID_TEXT)
        else:
            self.install_status_label.setText(self.INSTALL_INVALID_TEXT)
