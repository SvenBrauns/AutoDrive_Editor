"""The buildings of a savegame with their sheds and stations.

    placeables.xml
        <placeable filename="data/placeables/easySheds/easyShed01/easyShed01.xml"
            uniqueId="…" position="-354.456 84.894 1207.828" rotation="0.00 -38.34 0.00">
        <placeable isPreplaced="true" uniqueId="preplaced_stable01_23d4…"/>

Placed buildings have their position and rotation here; the map's own buildings are found in the
map scene (see building_definitions.read_preplaced). Each building file is read once.
"""

import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import dataclass, field, replace
from enum import StrEnum
from pathlib import Path

from autodrive_editor.error_log import logger
from autodrive_editor.file_io.building_definitions import (
    READ_ERRORS,
    BuildingScene,
    Transform,
    building_name,
    category_label,
    floats,
    map_scene,
    read_preplaced,
    rotation_matrix,
)
from autodrive_editor.file_io.game_files import GameFiles, locate
from autodrive_editor.file_io.savegame_sheds import IndoorArea, local_areas, placed_area
from autodrive_editor.file_io.savegame_stations import TRIGGERS, Stop, local_stops, placed_stop
from autodrive_editor.i18n import tr


class BuildingGroup(StrEnum):
    """What the editor does with a building type. Each type belongs to exactly one group."""

    STATIONS = "stations"
    SHEDS = "sheds"
    BUNKER_SILOS = "bunker_silos"
    OTHER = "other"

    @property
    def label(self) -> str:
        return {
            BuildingGroup.STATIONS: tr("Stations"),
            BuildingGroup.SHEDS: tr("Sheds"),
            BuildingGroup.BUNKER_SILOS: tr("Bunker silos"),
            BuildingGroup.OTHER: tr("Other"),
        }[self]


@dataclass(frozen=True)
class BuildingType:
    """A building file with indoor areas, stations or a bunker silo, and how often it is in the
    savegame. group is the group its definition gives."""

    building_file: str
    name: str
    category: str
    group: BuildingGroup
    count: int = 0

    @property
    def category_label(self) -> str:
        return category_label(self.category)


@dataclass
class SavegameBuildings:
    types: list[BuildingType] = field(default_factory=list)
    areas: list[IndoorArea] = field(default_factory=list)
    stops: list[Stop] = field(default_factory=list)
    # Building files and savegame files that could not be read.
    failed: list[str] = field(default_factory=list)


def read_savegame_buildings(savegame_directory: Path, files: GameFiles) -> SavegameBuildings:
    placed, failed = placed_buildings(savegame_directory, files)
    # Type, indoor areas and stops by building file; None if not readable or of no use.
    definitions: dict[str, tuple | None] = {}
    counts = Counter()
    result = SavegameBuildings(failed=failed)

    for building_file, unique_id, placement in placed:
        if building_file not in definitions:
            try:
                definitions[building_file] = read_definition(building_file, files)
            except READ_ERRORS as error:
                logger.warning("Building %s could not be read: %s", building_file, error)
                definitions[building_file] = None
                result.failed.append(building_file)

        if definitions[building_file] is None:
            continue

        building_type, areas, stops = definitions[building_file]
        counts[building_file] += 1
        name, category = building_type.name, building_type.category

        result.areas += [
            placed_area(points, placement, building_file, unique_id, name, category)
            for points in areas
        ]
        result.stops += [
            placed_stop(stop, placement, building_file, unique_id, name) for stop in stops
        ]

    result.types = [
        replace(definition[0], count=counts[building_file])
        for building_file, definition in definitions.items()
        if definition is not None
    ]

    return result


def placed_buildings(
    savegame_directory: Path, files: GameFiles
) -> tuple[list[tuple[str, str, Transform]], list[str]]:
    """(building file, unique id, placement) of the savegame's placed and preplaced buildings,
    and the savegame files that could not be read."""

    path = Path(savegame_directory) / "placeables.xml"

    if not path.is_file():
        return [], []

    try:
        placeables = ET.parse(path).getroot().findall("placeable")
    except ET.ParseError as error:
        logger.warning("%s could not be read: %s", path, error)
        return [], [str(path)]

    # Building file and placement of the map's buildings, by unique id.
    preplaced: dict[str, tuple[str, Transform]] = {}
    failed = []

    if any(placeable.get("isPreplaced") == "true" for placeable in placeables):
        try:
            preplaced = read_preplaced(files.read(*map_scene(savegame_directory, files)))
        except READ_ERRORS as error:
            logger.warning("The map of %s could not be read: %s", savegame_directory, error)
            failed.append(str(Path(savegame_directory) / "careerSavegame.xml"))

    buildings = []

    for placeable in placeables:
        unique_id = placeable.get("uniqueId", "")

        if placeable.get("isPreplaced") == "true":
            if unique_id not in preplaced:
                continue

            building_file, placement = preplaced[unique_id]
        else:
            building_file = placeable.get("filename", "")
            position = placeable.get("position")

            if not building_file or position is None:
                continue

            rotation = rotation_matrix(floats(placeable.get("rotation", "0 0 0")))
            placement = (rotation, floats(position))

        buildings.append((building_file, unique_id, placement))

    return buildings, failed


def read_definition(building_file: str, files: GameFiles) -> tuple | None:
    """(type, indoor areas, stops) of a building file, None if it has none of them and is no
    bunker silo. See savegame_sheds and savegame_stations."""

    mod, path = locate(building_file)
    definition = ET.fromstring(files.read(mod, path))
    group = default_group(definition)

    if group == BuildingGroup.OTHER:
        return None

    building_type = BuildingType(
        building_file=building_file,
        name=building_name(definition, building_file, mod, files),
        category=(definition.findtext("storeData/category") or "").strip(),
        group=group,
    )
    # A bunker silo may have neither.
    if definition.find("indoorAreas/indoorArea") is None and not _has_triggers(definition):
        return building_type, [], []

    scene = BuildingScene(definition, mod, files)

    return building_type, local_areas(definition, scene), local_stops(definition, scene)


def default_group(definition) -> BuildingGroup:
    if definition.find(".//bunkerSilo") is not None:
        return BuildingGroup.BUNKER_SILOS

    if _has_triggers(definition):
        return BuildingGroup.STATIONS

    if definition.find("indoorAreas/indoorArea") is not None:
        return BuildingGroup.SHEDS

    return BuildingGroup.OTHER


def _has_triggers(definition) -> bool:
    return any(element.tag in TRIGGERS for element in definition.iter())
