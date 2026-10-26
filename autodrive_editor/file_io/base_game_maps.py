"""The base game maps in the FS25 install folder.

They lie unpacked under <install>\\data\\maps\\mapUS, mapEU and mapAS and
are read like map mods. Their files refer to each other with paths that
start with "$data/", meaning the game's data folder. Base maps have no
modDesc.xml; their titles come from the game's packed language files,
so they are listed here. AutoDrive names them like mod maps, e.g.
"Riverbend Springs" -> "Riverbend_Springs".
"""

from pathlib import Path, PurePosixPath

from autodrive_editor.file_io.map_mod import MapMod, read_map_entry
from autodrive_editor.file_io.mod_archive import ModArchive
from autodrive_editor.i18n import tr

BASE_GAME_MOD_NAME = "FS25 Grundspiel"

# Folder under data\maps -> map title (the same in every language).
BASE_GAME_MAPS = {
    "mapUS": "Riverbend Springs",
    "mapEU": "Zielonka",
    "mapAS": "Hutan Pantai",
}

DATA_PREFIX = "$data/"


class GameDataArchive(ModArchive):
    """Read access to the game's data folder. Unlike a mod folder it is not
    listed completely (it holds many thousands of files); paths are
    checked when they are used."""

    def __init__(self, data_directory: str | Path):
        self.path = Path(data_directory)
        self._zip = None

        if not self.path.is_dir():
            raise FileNotFoundError(tr("Game data not found: {path}", path=self.path))

    @property
    def name(self) -> str:
        return BASE_GAME_MOD_NAME

    def resolve(self, name: str) -> str | None:
        name = name.replace("\\", "/")

        if name.startswith(DATA_PREFIX):
            name = name[len(DATA_PREFIX) :]

        normalized = str(PurePosixPath(name))

        return normalized if (self.path / normalized).is_file() else None


def read_base_game_maps(data_directory: str | Path) -> MapMod | None:
    """The base game maps found in the data folder."""

    data_directory = Path(data_directory)
    entries = []

    with GameDataArchive(data_directory) as archive:
        for folder, title in BASE_GAME_MAPS.items():
            entry = read_map_entry(
                archive,
                map_id=folder,
                titles={"en": title},
                config_filename=f"maps/{folder}/{folder}.xml",
            )

            if entry is not None:
                entries.append(entry)

    if not entries:
        return None

    return MapMod(path=data_directory, name=BASE_GAME_MOD_NAME, maps=entries, is_base_game=True)


def open_mod_archive(map_mod: MapMod) -> ModArchive:
    """The archive to read a map mod's files from."""

    if map_mod.is_base_game:
        return GameDataArchive(map_mod.path)

    return ModArchive(map_mod.path)
