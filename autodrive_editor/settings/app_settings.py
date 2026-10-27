"""Settings that are kept between editor sessions."""

from pathlib import Path

from PySide6.QtCore import QSettings

from autodrive_editor.editing.path_shapes import PathOptions
from autodrive_editor.game.game_folder import GameFolder
from autodrive_editor.game.game_installation import GameInstallation
from autodrive_editor.i18n import LANGUAGES, system_language
from autodrive_editor.model.connections import ConnectionType
from autodrive_editor.paths import user_data_directory


class AppSettings:
    """Reads and writes settings.ini in the editor's user data folder."""

    GAME_FOLDER_KEY = "game/folder"
    INSTALL_FOLDER_KEY = "game/install_folder"
    SETUP_DONE_KEY = "app/setup_done"
    MARKER_NAMES_KEY = "view/marker_names"
    AUTOSAVE_MINUTES_KEY = "app/autosave_minutes"
    PATH_SPACING_KEY = "path/spacing"
    PATH_CONNECTION_KEY = "path/connection_type"
    PATH_FLAG_KEY = "path/flag"
    LANGUAGE_KEY = "app/language"
    CHECK_OVERLAP_KEY = "check/overlap_tolerance"
    CHECK_HEIGHT_KEY = "check/max_height_difference"

    DEFAULT_AUTOSAVE_MINUTES = 5
    DEFAULT_OVERLAP_TOLERANCE = 0.1
    DEFAULT_MAX_HEIGHT_DIFFERENCE = 5.0

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
    def language(self) -> str:
        """The chosen language. Until one is chosen, it follows Windows."""

        value = self._settings.value(self.LANGUAGE_KEY, "")

        return value if value in LANGUAGES else system_language()

    def set_language(self, language: str):
        self._settings.setValue(self.LANGUAGE_KEY, language)
        self._settings.sync()

    @property
    def path_options(self) -> PathOptions:
        """Options of the line and curve tools. Unknown stored values fall
        back to the defaults."""

        default = PathOptions()

        try:
            return PathOptions(
                spacing=self._settings.value(self.PATH_SPACING_KEY, default.spacing, type=float),
                connection_type=ConnectionType(
                    self._settings.value(self.PATH_CONNECTION_KEY, default.connection_type.value)
                ),
                flag=self._settings.value(self.PATH_FLAG_KEY, default.flag, type=int),
            )

        except ValueError:
            return default

    def set_path_options(self, options: PathOptions):
        self._settings.setValue(self.PATH_SPACING_KEY, float(options.spacing))
        self._settings.setValue(self.PATH_CONNECTION_KEY, options.connection_type.value)
        self._settings.setValue(self.PATH_FLAG_KEY, int(options.flag))
        self._settings.sync()

    @property
    def check_tolerances(self) -> tuple[float, float]:
        """Network check: overlap distance and largest height difference
        from the terrain, in metres."""

        return (
            self._settings.value(
                self.CHECK_OVERLAP_KEY, self.DEFAULT_OVERLAP_TOLERANCE, type=float
            ),
            self._settings.value(
                self.CHECK_HEIGHT_KEY, self.DEFAULT_MAX_HEIGHT_DIFFERENCE, type=float
            ),
        )

    def set_check_tolerances(self, overlap_tolerance: float, max_height_difference: float):
        self._settings.setValue(self.CHECK_OVERLAP_KEY, float(overlap_tolerance))
        self._settings.setValue(self.CHECK_HEIGHT_KEY, float(max_height_difference))
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
