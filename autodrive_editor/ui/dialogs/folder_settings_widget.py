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
from autodrive_editor.i18n import tr
from autodrive_editor.settings.app_settings import AppSettings


class FolderSettingsWidget(QWidget):
    """Input fields with status for the FS25 user folder (AutoDrive routes,
    savegames, map mods) and the FS25 install folder (base game maps).
    Nothing is stored until store() is called."""

    VALID_TEXT = tr("✔ FS25 folder found")
    INVALID_TEXT = tr("✖ Not an FS25 user folder (game.xml is missing)")
    EMPTY_TEXT = tr("No folder chosen")

    INSTALL_VALID_TEXT = tr("✔ FS25 installation found")
    INSTALL_INVALID_TEXT = tr(
        "✖ Not an FS25 installation ({executable} or data\\maps is missing)",
        executable=GAME_EXECUTABLE,
    )

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
        group = QGroupBox(tr("Game folder"), self)

        self.game_folder_input = QLineEdit(group)
        self.game_folder_input.setPlaceholderText(str(GameFolder.default_path()))
        self.game_folder_input.textChanged.connect(self._update_status)

        self.status_label = QLabel(group)

        self._fill_group(
            group,
            tr("FS25 folder:"),
            self.game_folder_input,
            self.status_label,
            self._browse,
            self._detect,
            tr(
                "The FS25 user folder contains the savegames, the mods folder and the "
                "AutoDrive routes (modSettings\\FS25_AutoDrive\\routesManager)."
            ),
        )

        return group

    def _create_install_group(self) -> QGroupBox:
        group = QGroupBox(tr("Installation folder"), self)

        self.install_folder_input = QLineEdit(group)
        self.install_folder_input.textChanged.connect(self._update_install_status)

        self.install_status_label = QLabel(group)

        self._fill_group(
            group,
            tr("FS25 installation:"),
            self.install_folder_input,
            self.install_status_label,
            self._browse_install,
            self._detect_install,
            tr(
                "The folder FS25 is installed in (on Steam e.g. "
                "steamapps\\common\\Farming Simulator 25). It contains the base game maps "
                "Riverbend Springs, Zielonka and Hutan Pantai."
            ),
        )

        return group

    @staticmethod
    def _fill_group(group, label, folder_input, status_label, browse, detect, hint_text):
        browse_button = QPushButton(tr("Browse…"), group)
        browse_button.clicked.connect(browse)

        detect_button = QPushButton(tr("Detect automatically"), group)
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

        chosen = QFileDialog.getExistingDirectory(self, tr("Choose the FS25 user folder"), start)

        if chosen:
            self.game_folder_input.setText(str(Path(chosen)))

    def _detect(self):
        detected = GameFolder.detect()

        if detected is not None:
            self.game_folder_input.setText(str(detected.path))
        else:
            self.status_label.setText(
                tr(
                    "✖ Not found at {path}. Please choose it with “Browse…”.",
                    path=GameFolder.default_path(),
                )
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

        chosen = QFileDialog.getExistingDirectory(
            self, tr("Choose the FS25 installation folder"), start
        )

        if chosen:
            self.install_folder_input.setText(str(Path(chosen)))

    def _detect_install(self):
        detected = GameInstallation.detect()

        if detected is not None:
            self.install_folder_input.setText(str(detected.path))
        else:
            self.install_status_label.setText(tr("✖ Not found. Please choose it with “Browse…”."))

    def _update_install_status(self):
        installation = self.chosen_installation

        if installation is None:
            self.install_status_label.setText(self.EMPTY_TEXT)
        elif installation.is_valid:
            self.install_status_label.setText(self.INSTALL_VALID_TEXT)
        else:
            self.install_status_label.setText(self.INSTALL_INVALID_TEXT)
