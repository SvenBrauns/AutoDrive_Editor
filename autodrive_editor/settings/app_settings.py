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
    SETUP_DONE_KEY = "app/setup_done"
    MARKER_NAMES_KEY = "view/marker_names"
    AUTOSAVE_MINUTES_KEY = "app/autosave_minutes"

    DEFAULT_AUTOSAVE_MINUTES = 5

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

    @property
    def marker_names_visible(self) -> bool:
        return self._settings.value(self.MARKER_NAMES_KEY, True, type=bool)

    def set_marker_names_visible(self, visible: bool):
        self._settings.setValue(self.MARKER_NAMES_KEY, bool(visible))
        self._settings.sync()

    @property
    def autosave_minutes(self) -> int:
        """Minutes between autosaves; 0 turns autosave off."""

        return self._settings.value(
            self.AUTOSAVE_MINUTES_KEY, self.DEFAULT_AUTOSAVE_MINUTES, type=int
        )

    def set_autosave_minutes(self, minutes: int):
        self._settings.setValue(self.AUTOSAVE_MINUTES_KEY, max(0, int(minutes)))
        self._settings.sync()

    @property
    def needs_setup(self) -> bool:
        """True on the first start, and when a stored folder no longer
        exists (e.g. the game was moved to another drive)."""

        if not self._settings.value(self.SETUP_DONE_KEY, False, type=bool):
            return True

        game_folder = self.game_folder
        installation = self.install_folder

        return (game_folder is not None and not game_folder.is_valid) or (
            installation is not None and not installation.is_valid
        )

    def mark_setup_done(self):
        self._settings.setValue(self.SETUP_DONE_KEY, True)
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
