"""Settings that are kept between editor sessions."""

from pathlib import Path

from PySide6.QtCore import QSettings

from autodrive_editor.game.game_folder import GameFolder
from autodrive_editor.game.game_installation import GameInstallation
from autodrive_editor.paths import user_data_directory


class AppSettings:
    """Reads and writes settings.ini in the editor's user data folder."""

    GAME_FOLDER_KEY = "game/folder"
    INSTALL_FOLDER_KEY = "game/install_folder"

    def __init__(self, settings_path: Path | None = None):
        if settings_path is None:
            settings_path = user_data_directory() / "settings.ini"

        settings_path.parent.mkdir(parents=True, exist_ok=True)

        self.settings_path = settings_path
        self._settings = QSettings(str(settings_path), QSettings.Format.IniFormat)

    @property
    def game_folder(self) -> GameFolder | None:
        value = self._settings.value(self.GAME_FOLDER_KEY, "")

        return GameFolder(value) if value else None

    def set_game_folder(self, path: str | Path | None):
        if path:
            self._settings.setValue(self.GAME_FOLDER_KEY, str(Path(path)))
        else:
            self._settings.remove(self.GAME_FOLDER_KEY)

        self._settings.sync()

    @property
    def install_folder(self) -> GameInstallation | None:
        value = self._settings.value(self.INSTALL_FOLDER_KEY, "")

        return GameInstallation(value) if value else None

    def set_install_folder(self, path: str | Path | None):
        if path:
            self._settings.setValue(self.INSTALL_FOLDER_KEY, str(Path(path)))
        else:
            self._settings.remove(self.INSTALL_FOLDER_KEY)

        self._settings.sync()

    def ensure_install_folder(self) -> GameInstallation | None:
        """Like ensure_game_folder, for the FS25 install folder."""

        if self.install_folder is None:
            detected = GameInstallation.detect()

            if detected is not None:
                self.set_install_folder(detected.path)

        return self.install_folder

    def ensure_game_folder(self) -> GameFolder | None:
        """Returns the configured game folder. On first start, when none is
        set yet, the default location is detected and stored."""

        if self.game_folder is None:
            detected = GameFolder.detect()

            if detected is not None:
                self.set_game_folder(detected.path)

        return self.game_folder
