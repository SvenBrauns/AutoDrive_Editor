"""What the editor shows about a savegame, read from careerSavegame.xml.

<careerSavegame>
    <settings>
        <savegameName>Mein Spielstand</savegameName>
        <mapId>FS25_Thueringen_2_0_16x.SampleModMap</mapId>
        <mapTitle>LS25 Thüringen 2.0 16x</mapTitle>
        <saveDateFormatted>23.10.2026</saveDateFormatted>
    </settings>
</careerSavegame>
"""

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from autodrive_editor.game.game_folder import GameFolder

AUTODRIVE_CONFIG_NAME = "AutoDrive_config.xml"


@dataclass(frozen=True)
class SavegameInfo:
    directory: Path
    number: int
    name: str = ""
    map_title: str = ""
    map_id: str = ""
    save_date: str = ""

    @property
    def autodrive_config_path(self) -> Path:
        return self.directory / AUTODRIVE_CONFIG_NAME

    @property
    def display_name(self) -> str:
        return self.name or f"Savegame {self.number}"


def read_savegame_info(directory: Path) -> SavegameInfo:
    directory = Path(directory)
    number = int(directory.name.removeprefix("savegame") or 0)
    career = directory / "careerSavegame.xml"

    if not career.is_file():
        return SavegameInfo(directory=directory, number=number)

    try:
        settings = ET.parse(career).getroot().find("settings")
    except ET.ParseError:
        settings = None

    def text(tag: str) -> str:
        return (settings.findtext(tag) or "").strip() if settings is not None else ""

    return SavegameInfo(
        directory=directory,
        number=number,
        name=text("savegameName"),
        map_title=text("mapTitle"),
        map_id=text("mapId"),
        save_date=text("saveDateFormatted"),
    )


def savegames_with_autodrive(game_folder: GameFolder) -> list[SavegameInfo]:
    """Savegames that contain AutoDrive data, ordered by number."""

    return [
        read_savegame_info(directory)
        for directory in game_folder.savegame_directories()
        if (directory / AUTODRIVE_CONFIG_NAME).is_file()
    ]
