"""The Farming Simulator 25 user folder and where AutoDrive keeps its files.

Layout of the folder, normally Documents\\My Games\\FarmingSimulator2025:

    modSettings\\FS25_AutoDrive\\routesManager\\routes.xml   route list
    modSettings\\FS25_AutoDrive\\routesManager\\routes\\      route files
    savegame1 … savegame20\\AutoDrive_config.xml          AutoDrive data per savegame
    mods\\                                                 installed mods
"""

from pathlib import Path

from PySide6.QtCore import QStandardPaths

GAME_FOLDER_NAME = "FarmingSimulator2025"

# Files that only exist in a real FS25 user folder.
GAME_FOLDER_MARKERS = ("game.xml", "gameSettings.xml")


class GameFolder:
    """Paths inside an FS25 user folder."""

    def __init__(self, path: str | Path):
        self.path = Path(path)

    @property
    def is_valid(self) -> bool:
        return self.path.is_dir() and any(
            (self.path / marker).is_file() for marker in GAME_FOLDER_MARKERS
        )

    @property
    def routes_manager_directory(self) -> Path:
        return self.path / "modSettings" / "FS25_AutoDrive" / "routesManager"

    @property
    def routes_xml_path(self) -> Path:
        return self.routes_manager_directory / "routes.xml"

    @property
    def routes_directory(self) -> Path:
        return self.routes_manager_directory / "routes"

    @property
    def mods_directory(self) -> Path:
        return self.path / "mods"

    def savegame_directories(self) -> list[Path]:
        """All savegameN folders, ordered by their number."""

        folders = [
            folder
            for folder in self.path.glob("savegame*")
            if folder.is_dir() and folder.name.removeprefix("savegame").isdigit()
        ]

        return sorted(folders, key=lambda folder: int(folder.name.removeprefix("savegame")))

    @staticmethod
    def default_path() -> Path:
        """Where FS25 puts its user folder. Uses the Windows Documents
        location, which also covers a Documents folder moved to OneDrive."""

        documents = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.DocumentsLocation
        )

        return Path(documents) / "My Games" / GAME_FOLDER_NAME

    @classmethod
    def detect(cls) -> "GameFolder | None":
        """The game folder at the default location, if it exists."""

        folder = cls(cls.default_path())

        return folder if folder.is_valid else None
