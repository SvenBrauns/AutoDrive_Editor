"""The two FS25 folders the editor needs, shared by the settings dialog
and the first-start dialog."""

from pathlib import Path

from PySide6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from autodrive_editor.game.game_folder import GameFolder
from autodrive_editor.game.game_installation import GAME_EXECUTABLE, GameInstallation
from autodrive_editor.settings.app_settings import AppSettings


class FolderSettingsWidget(QWidget):
    """Input fields with status for the FS25 user folder (AutoDrive routes,
    savegames, map mods) and the FS25 install folder (base game maps).
    Nothing is stored until store() is called."""

    VALID_TEXT = "✔ FS25-Ordner gefunden"
    INVALID_TEXT = "✖ Kein FS25-Benutzerordner (game.xml fehlt)"
    EMPTY_TEXT = "Kein Ordner gewählt"

    INSTALL_VALID_TEXT = "✔ FS25-Installation gefunden"
    INSTALL_INVALID_TEXT = f"✖ Keine FS25-Installation ({GAME_EXECUTABLE} oder data\\maps fehlt)"

    def __init__(self, settings: AppSettings, parent=None):
        super().__init__(parent)

        self.settings = settings

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._create_game_group())
        layout.addWidget(self._create_install_group())

        game_folder = settings.game_folder
        self.game_folder_input.setText(str(game_folder.path) if game_folder else "")
        self._update_status()

        installation = settings.install_folder
        self.install_folder_input.setText(str(installation.path) if installation else "")
        self._update_install_status()

    @property
    def chosen_folder(self) -> GameFolder | None:
        text = self.game_folder_input.text().strip()

        return GameFolder(text) if text else None

    @property
    def chosen_installation(self) -> GameInstallation | None:
        text = self.install_folder_input.text().strip()

        return GameInstallation(text) if text else None

    def store(self):
        folder = self.chosen_folder
        self.settings.set_game_folder(folder.path if folder else None)

        installation = self.chosen_installation
        self.settings.set_install_folder(installation.path if installation else None)

    def _create_game_group(self) -> QGroupBox:
        group = QGroupBox("Spielordner", self)

        self.game_folder_input = QLineEdit(group)
        self.game_folder_input.setPlaceholderText(str(GameFolder.default_path()))
        self.game_folder_input.textChanged.connect(self._update_status)

        self.status_label = QLabel(group)

        self._fill_group(
            group,
            "FS25-Ordner:",
            self.game_folder_input,
            self.status_label,
            self._browse,
            self._detect,
            "Der FS25-Benutzerordner enthält die Savegames, den Mods-Ordner und die "
            "AutoDrive-Routen (modSettings\\FS25_AutoDrive\\routesManager).",
        )

        return group

    def _create_install_group(self) -> QGroupBox:
        group = QGroupBox("Installationsordner", self)

        self.install_folder_input = QLineEdit(group)
        self.install_folder_input.textChanged.connect(self._update_install_status)

        self.install_status_label = QLabel(group)

        self._fill_group(
            group,
            "LS25-Installation:",
            self.install_folder_input,
            self.install_status_label,
            self._browse_install,
            self._detect_install,
            "Der Ordner, in dem LS25 installiert ist (bei Steam z. B. "
            "steamapps\\common\\Farming Simulator 25). Er enthält die Grundspiel-Karten "
            "Riverbend Springs, Zielonka und Hutan Pantai.",
        )

        return group

    @staticmethod
    def _fill_group(group, label, folder_input, status_label, browse, detect, hint_text):
        browse_button = QPushButton("Durchsuchen…", group)
        browse_button.clicked.connect(browse)

        detect_button = QPushButton("Automatisch erkennen", group)
        detect_button.clicked.connect(detect)

        folder_row = QHBoxLayout()
        folder_row.addWidget(folder_input, 1)
        folder_row.addWidget(browse_button)
        folder_row.addWidget(detect_button)

        hint = QLabel(hint_text, group)
        hint.setWordWrap(True)

        form = QFormLayout(group)
        form.addRow(label, folder_row)
        form.addRow("", status_label)
        form.addRow(hint)

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
