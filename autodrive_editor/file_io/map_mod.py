"""Finds the maps in a map mod and where their image and heightmap are.

    modDesc.xml
        <maps><map id="SampleModMap" configFilename="maps/config/mapEU.xml">
            <title><en>LS25 Thüringen 2.0 16x</en></title>
        </map></maps>

    maps/config/mapEU.xml  (map config)
        <map width="8192" imageFilename="maps/overview.png">
            <filename>maps/map.i3d</filename>

    maps/map.i3d  (3D scene, names the terrain heightmap)
        <File fileId="…" filename="data/dem.png"/>

The map image is stored as .dds although the config names a .png. The
map size is width / 2048. AutoDrive identifies a map by its title with
spaces and dots replaced by "_".
"""

import posixpath
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

from autodrive_editor.file_io.mod_archive import ModArchive
from autodrive_editor.i18n import ENGLISH, GERMAN, current_language, tr

BASE_MAP_SIZE = 2048
SUPPORTED_MAP_SCALES = (1, 2, 4, 8)


def pick_title(titles: dict[str, str], fallback: str) -> str:
    """The title in the editor's language, else English, German or any."""

    for language in (current_language(), ENGLISH, GERMAN):
        if titles.get(language):
            return titles[language]

    return next(iter(titles.values()), fallback)


def autodrive_map_name(title: str) -> str:
    """The name AutoDrive uses for a map: its title with spaces and dots
    replaced by underscores."""

    return re.sub(r"[ .]", "_", title.strip())


@dataclass(frozen=True)
class MapEntry:
    """One map of a mod."""

    map_id: str
    titles: dict[str, str]
    config_file: str
    width: int
    image_file: str | None
    heightmap_file: str | None

    @property
    def title(self) -> str:
        return pick_title(self.titles, self.map_id)

    @property
    def autodrive_names(self) -> list[str]:
        """All names AutoDrive might use, one per title language."""

        names = []

        for title in self.titles.values():
            name = autodrive_map_name(title)

            if name and name not in names:
                names.append(name)

        return names

    @property
    def map_scale(self) -> int | None:
        scale, remainder = divmod(self.width, BASE_MAP_SIZE)

        if remainder or scale not in SUPPORTED_MAP_SCALES:
            return None

        return scale

    @property
    def problems(self) -> list[str]:
        """Why the map cannot be imported, empty if it can."""

        problems = []

        if self.image_file is None:
            problems.append(tr("Map image (overview.dds) not found"))

        if self.map_scale is None:
            problems.append(tr("Map size {width} m is not supported", width=self.width))

        return problems


@dataclass(frozen=True)
class MapMod:
    path: Path
    name: str
    maps: list[MapEntry] = field(default_factory=list)

    # Base game maps are read from the game's data folder.
    is_base_game: bool = False


def read_map_mod(path: str | Path) -> MapMod | None:
    """The maps of a mod, or None if the mod contains no map."""

    with ModArchive(path) as archive:
        if not archive.exists("modDesc.xml"):
            return None

        mod_desc = ET.fromstring(archive.read("modDesc.xml"))
        maps = [
            entry
            for element in mod_desc.iter("map")
            if (entry := _read_mod_desc_map(archive, element)) is not None
        ]

        if not maps:
            return None

        return MapMod(path=Path(path), name=archive.name, maps=maps)


def _read_mod_desc_map(archive: ModArchive, element) -> MapEntry | None:
    """A <map> entry of modDesc.xml."""

    title_element = element.find("title")

    titles = {
        child.tag: (child.text or "").strip()
        for child in (title_element if title_element is not None else [])
        if (child.text or "").strip()
    }

    return read_map_entry(
        archive,
        map_id=element.get("id", ""),
        titles=titles,
        config_filename=element.get("configFilename", ""),
    )


def read_map_entry(
    archive: ModArchive, map_id: str, titles: dict[str, str], config_filename: str
) -> MapEntry | None:
    """A map from its config file, or None if the config is missing."""

    config_file = archive.resolve(config_filename)

    if config_file is None:
        return None

    config = ET.fromstring(archive.read(config_file))

    width = config.get("width", "0")
    i3d_file = archive.resolve((config.findtext("filename") or "").strip())

    return MapEntry(
        map_id=map_id,
        titles=titles,
        config_file=config_file,
        width=int(width) if width.isdigit() else 0,
        image_file=_find_image_file(archive, config.get("imageFilename", "")),
        heightmap_file=_find_heightmap_file(archive, i3d_file) if i3d_file else None,
    )


def _find_image_file(archive: ModArchive, image_filename: str) -> str | None:
    """The overview image; mods ship it as .dds even if the config names
    a .png."""

    if not image_filename:
        return None

    stem = posixpath.splitext(image_filename)[0]

    return archive.resolve(stem + ".dds") or archive.resolve(image_filename)


def _find_heightmap_file(archive: ModArchive, i3d_file: str) -> str | None:
    """The dem.png named in the map's i3d. The heightmap reference is near
    the top of the file, so parsing stops there."""

    with archive.open(i3d_file) as stream:
        for _, element in ET.iterparse(stream, events=("end",)):
            if element.tag == "File":
                filename = element.get("filename", "")

                if filename.lower().endswith("dem.png"):
                    # "$data/..." paths point into the game's data folder.
                    if filename.startswith("$"):
                        return archive.resolve(filename)

                    relative = posixpath.join(posixpath.dirname(i3d_file), filename)
                    return archive.resolve(posixpath.normpath(relative))

            element.clear()

    return None
