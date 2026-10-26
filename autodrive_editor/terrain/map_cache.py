"""Map images and heightmaps imported from map mods, kept in the editor's
user data folder so a mod only has to be imported once.

    <user data>\\maps\\<folder>\\
        overview.png   map image, already cut to the map area (2048 px)
        dem.png        terrain heightmap, as in the mod
        map.json       names, titles, map size and which mod it came from

The editor ships no map images; each user imports them from their own
mods.
"""

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from autodrive_editor.file_io.background_image import map_image_from_dds_bytes
from autodrive_editor.file_io.base_game_maps import open_mod_archive
from autodrive_editor.file_io.map_mod import MapEntry, MapMod, pick_title
from autodrive_editor.file_io.mod_archive import ModArchive
from autodrive_editor.paths import user_data_directory

INFO_FILE = "map.json"
OVERVIEW_FILE = "overview.png"
HEIGHTMAP_FILE = "dem.png"


@dataclass(frozen=True)
class CachedMap:
    directory: Path
    titles: dict[str, str]
    fallback_title: str
    autodrive_names: list[str]
    map_scale: int
    mod_name: str
    map_id: str
    config_file: str

    @property
    def title(self) -> str:
        return pick_title(self.titles, self.fallback_title)

    @property
    def overview_path(self) -> Path:
        return self.directory / OVERVIEW_FILE

    @property
    def heightmap_path(self) -> Path | None:
        path = self.directory / HEIGHTMAP_FILE
        return path if path.is_file() else None

    @property
    def source_key(self) -> tuple[str, str]:
        """Identifies the map inside its mod."""

        return (self.mod_name, self.config_file)


class MapCache:
    def __init__(self, directory: Path | None = None):
        self.directory = directory or user_data_directory() / "maps"

    def maps(self) -> list[CachedMap]:
        """All imported maps, by title."""

        if not self.directory.is_dir():
            return []

        found = [
            cached
            for folder in self.directory.iterdir()
            if (cached := self._read(folder)) is not None
        ]

        return sorted(found, key=lambda cached: cached.title.lower())

    def find(self, autodrive_map_name: str | None) -> CachedMap | None:
        """The imported map AutoDrive calls by this name."""

        if not autodrive_map_name:
            return None

        return next(
            (cached for cached in self.maps() if autodrive_map_name in cached.autodrive_names),
            None,
        )

    def find_import(self, mod_name: str, map_entry: MapEntry) -> CachedMap | None:
        key = (mod_name, map_entry.config_file)

        return next((cached for cached in self.maps() if cached.source_key == key), None)

    def import_map(self, mod: MapMod | Path, map_entry: MapEntry) -> CachedMap:
        """Extracts image and heightmap of one map from a mod (or the base
        game). Importing the same map again replaces the earlier import."""

        if map_entry.problems:
            raise ValueError("; ".join(map_entry.problems))

        archive = open_mod_archive(mod) if isinstance(mod, MapMod) else ModArchive(mod)

        with archive:
            existing = self.find_import(archive.name, map_entry)
            folder = existing.directory if existing else self._new_folder(map_entry)
            folder.mkdir(parents=True, exist_ok=True)

            map_image = map_image_from_dds_bytes(archive.read(map_entry.image_file))
            map_image.save(folder / OVERVIEW_FILE)

            if map_entry.heightmap_file:
                (folder / HEIGHTMAP_FILE).write_bytes(archive.read(map_entry.heightmap_file))

            info = {
                "title": map_entry.title,
                "titles": map_entry.titles,
                "autodrive_names": map_entry.autodrive_names,
                "map_scale": map_entry.map_scale,
                "mod_name": archive.name,
                "map_id": map_entry.map_id,
                "config_file": map_entry.config_file,
                "imported": datetime.now().isoformat(timespec="seconds"),
            }

        (folder / INFO_FILE).write_text(
            json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        return self._read(folder)

    def _new_folder(self, map_entry: MapEntry) -> Path:
        base = (
            re.sub(
                r"[^\w-]+",
                "_",
                map_entry.autodrive_names[0] if map_entry.autodrive_names else map_entry.map_id,
            ).strip("_")
            or "map"
        )
        folder = self.directory / base
        number = 2

        while folder.exists():
            folder = self.directory / f"{base}_{number}"
            number += 1

        return folder

    @staticmethod
    def _read(folder: Path) -> CachedMap | None:
        try:
            info = json.loads((folder / INFO_FILE).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None

        if not (folder / OVERVIEW_FILE).is_file():
            return None

        return CachedMap(
            directory=folder,
            # Imports from older versions only have "title".
            titles=dict(info.get("titles", {})),
            fallback_title=info.get("title", folder.name),
            autodrive_names=list(info.get("autodrive_names", [])),
            map_scale=int(info.get("map_scale", 1)),
            mod_name=info.get("mod_name", ""),
            map_id=info.get("map_id", ""),
            config_file=info.get("config_file", ""),
        )
