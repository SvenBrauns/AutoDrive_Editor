"""The Farming Simulator 25 installation folder, which holds the base game
maps under data\\maps."""

import re
from pathlib import Path

GAME_EXECUTABLE = "FarmingSimulator2025.exe"

STEAM_FOLDER_NAME = "Farming Simulator 25"
STEAM_LIBRARY_FILE = Path("C:/Program Files (x86)/Steam/steamapps/libraryfolders.vdf")

# Install folders of the Giants (non-Steam) version.
STANDALONE_PATHS = (
    Path("C:/Program Files (x86)/Farming Simulator 2025"),
    Path("C:/Program Files/Farming Simulator 2025"),
)


class GameInstallation:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    @property
    def is_valid(self) -> bool:
        return (self.path / GAME_EXECUTABLE).is_file() and self.base_maps_directory.is_dir()

    @property
    def data_directory(self) -> Path:
        return self.path / "data"

    @property
    def base_maps_directory(self) -> Path:
        return self.data_directory / "maps"

    @staticmethod
    def candidate_paths(steam_library_file: Path | None = None) -> list[Path]:
        """Folders where FS25 is usually installed: every Steam library plus
        the default Giants install folders."""

        if steam_library_file is None:
            steam_library_file = STEAM_LIBRARY_FILE

        candidates = []

        try:
            text = steam_library_file.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            text = ""

        for raw_path in re.findall(r'"path"\s+"([^"]+)"', text):
            library = Path(raw_path.replace("\\\\", "\\"))
            candidates.append(library / "steamapps" / "common" / STEAM_FOLDER_NAME)

        candidates.extend(STANDALONE_PATHS)

        return candidates

    @classmethod
    def detect(cls, steam_library_file: Path | None = None) -> "GameInstallation | None":
        for path in cls.candidate_paths(steam_library_file):
            installation = cls(path)

            if installation.is_valid:
                return installation

        return None
