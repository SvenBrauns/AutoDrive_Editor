"""Indoor areas of the buildings placed in a savegame, used as sheds.

    placeables.xml
        <placeable filename="data/placeables/easySheds/easyShed01/easyShed01.xml"
            uniqueId="…" position="-354.456 84.894 1207.828" rotation="0.00 -38.34 0.00">

    easyShed01.xml  (building definition)
        <storeData><name>$l10n_storeItem_easyShed01</name><category>sheds</category></storeData>
        <base><filename>$data/placeables/easySheds/easyShed01/easyShed01.i3d</filename></base>
        <indoorAreas><indoorArea startNode="indoorAreaStart01" widthNode="…" heightNode="…"/>
        <i3dMappings><i3dMapping id="indoorAreaStart01" node="0>2|0"/>

    easyShed01.i3d  (scene; "0>2|0" is child 0 of child 2 of the first component)
        <TransformGroup name="indoorAreaStart01" translation="-15 0 -7.5">
            <TransformGroup name="indoorAreaWidth01" translation="30 0 0"/>
            <TransformGroup name="indoorAreaHeight01" translation="0 0 15"/>

The name of a mod building is translated in its mod (modDesc.xml <l10n>, inline or in files
<filenamePrefix>_en.xml). The base game's translations are packed, so the key is turned into
words: "storeItem_mapUS_farmBarn" → "Farm barn".

Buildings that came with the map are listed in placeables.xml without a position:

    placeables.xml
        <placeable isPreplaced="true" uniqueId="preplaced_stable01_23d4…"/>

    careerSavegame.xml → modDesc.xml → map config → map.i3d  (see map_scene)

    map.i3d  (the building is a node of the map scene; the shed's position is that of its
              ReferenceNode, which can be slightly offset from the building node)
        <TransformGroup name="preplaced_stable01" translation="…" nodeId="33780">
            <TransformGroup name="placeable"><ReferenceNode name="stable01" referenceId="1575"/>
        <UserAttribute nodeId="33780">
            <Attribute name="onCreate" type="scriptCallback" value="Placeable.onCreate"/>
            <Attribute name="uniqueId" type="string" value="preplaced_stable01_23d4…"/>
            <Attribute name="xmlFilename" type="string" value="$data/placeables/…/stable01.xml"/>
"""

import io
import math
import re
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass
from pathlib import Path

from autodrive_editor.error_log import logger
from autodrive_editor.file_io.game_files import GameFiles, locate
from autodrive_editor.i18n import ENGLISH, current_language, tr

# 3 × 3 matrix and translation: point → matrix · point + translation.
Transform = tuple[tuple[tuple[float, ...], ...], tuple[float, float, float]]

IDENTITY: Transform = (((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)), (0.0, 0.0, 0.0))

L10N_PREFIX = "$l10n_"

# Left out of a translation key that is shown as the name: "storeItem_mapUS_farmBarn".
KEY_PREFIX = re.compile(r"^(storeItem_|shopItem_)?(map(US|EU|AS)_)?", re.IGNORECASE)

READ_ERRORS = (OSError, KeyError, IndexError, ValueError, ET.ParseError, zipfile.BadZipFile)


@dataclass(frozen=True)
class IndoorArea:
    """One indoor area of a placed building. corners are (x, z) on the map: the start, the end of
    its width, the opposite corner and the end of its height."""

    building_file: str
    unique_id: str
    corners: tuple[tuple[float, float], ...]
    # Ground height of the building.
    height: float
    name: str = ""
    # Shop category of the building, e.g. "sheds" or "productionPoints".
    category: str = ""

    @property
    def category_label(self) -> str:
        return category_label(self.category)


def read_sheds(savegame_directory: Path, files: GameFiles) -> tuple[list[IndoorArea], list[str]]:
    """The indoor areas of the savegame's placed buildings, and the building files that could not
    be read."""

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

    # Name, category and indoor areas in building coordinates, by building file; None if it could
    # not be read.
    building_areas: dict[str, tuple[str, str, list] | None] = {}
    areas = []

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

            rotation = _rotation_matrix(_floats(placeable.get("rotation", "0 0 0")))
            placement = (rotation, _floats(position))

        if building_file not in building_areas:
            try:
                building_areas[building_file] = read_building_areas(building_file, files)
            except READ_ERRORS as error:
                logger.warning("Building %s could not be read: %s", building_file, error)
                building_areas[building_file] = None

        if not building_areas[building_file]:
            continue

        name, category, local_areas = building_areas[building_file]

        for points in local_areas:
            start, width, height = (_apply(placement, point) for point in points)
            opposite = tuple(w + h - s for s, w, h in zip(start, width, height, strict=True))

            areas.append(
                IndoorArea(
                    building_file=building_file,
                    unique_id=unique_id,
                    corners=tuple((p[0], p[2]) for p in (start, width, opposite, height)),
                    height=placement[1][1],
                    name=name,
                    category=category,
                )
            )

    failed += [file for file, building in building_areas.items() if building is None]

    return areas, failed


def map_scene(savegame_directory: Path, files: GameFiles) -> tuple[str | None, str]:
    """(mod, path) of the map scene of a savegame. The map id in careerSavegame.xml is
    "FS25_SomeMod.SampleModMap" for a mod map, found in that mod's modDesc.xml, or "MapUS" for
    the base game map in data/maps/mapUS/mapUS.xml."""

    career = ET.parse(Path(savegame_directory) / "careerSavegame.xml").getroot()
    map_id = (career.findtext("settings/mapId") or "").strip()
    mod, _, mod_map_id = map_id.partition(".")

    if mod_map_id:
        maps = ET.fromstring(files.read(mod, "modDesc.xml")).findall("maps/map")
        config_file = {item.get("id"): item.get("configFilename", "") for item in maps}[mod_map_id]
    else:
        mod, folder = None, map_id[:1].lower() + map_id[1:]
        config_file = f"data/maps/{folder}/{folder}.xml"

    config = ET.fromstring(files.read(*locate(config_file, mod)))

    return locate(config.findtext("filename") or "", mod)


def read_preplaced(scene_data: bytes) -> dict[str, tuple[str, Transform]]:
    """Building file and placement of the buildings in a map scene, by unique id."""

    start = scene_data.rfind(b"<UserAttributes>")
    end = scene_data.rfind(b"</UserAttributes>")

    if start < 0 or end < start:
        return {}

    # Building nodes: node id → (building file, unique id). User attributes follow the scene.
    buildings = {}

    for node in ET.fromstring(scene_data[start : end + len(b"</UserAttributes>")]):
        attributes = {attribute.get("name"): attribute.get("value") for attribute in node}

        if attributes.get("onCreate") == "Placeable.onCreate" and attributes.get("xmlFilename"):
            buildings[node.get("nodeId")] = (
                attributes["xmlFilename"],
                attributes.get("uniqueId", ""),
            )

    preplaced = {}
    # Attributes of the scene elements from the root to the current one.
    path = []
    # Unique id and depth of the building being read, and whether its ReferenceNode was found.
    building, depth, referenced = None, 0, False

    for event, element in ET.iterparse(io.BytesIO(scene_data), events=("start", "end")):
        if event == "end":
            if element.tag == "Scene":
                break

            if path:
                path.pop()

            if len(path) < depth:
                building = None

            element.clear()
            continue

        if element.tag == "Scene":
            path = []
            continue

        path.append(element.attrib)
        node_id = element.get("nodeId")

        if building is None:
            if node_id not in buildings:
                continue

            building_file, building = buildings[node_id]
            depth, referenced = len(path), False
        elif element.tag == "ReferenceNode" and not referenced:
            referenced = True
        else:
            continue

        transform = IDENTITY

        for attributes in path:
            transform = _combine(transform, _local_transform(attributes))

        preplaced[building] = (building_file, transform)

    return preplaced


def read_building_areas(building_file: str, files: GameFiles) -> tuple[str, str, list]:
    """The name, category and indoor areas of a building definition, the areas as (start, width,
    height) points relative to the building. Without indoor areas name and category are empty."""

    mod, path = locate(building_file)
    definition = ET.fromstring(files.read(mod, path))
    indoor_areas = definition.findall("indoorAreas/indoorArea")

    if not indoor_areas:
        return "", "", []

    i3d_name = definition.findtext("base/filename") or definition.findtext("filename") or ""
    scene = ET.fromstring(files.read(*locate(i3d_name, mod))).find("Scene")

    mappings = {
        mapping.get("id"): mapping.get("node")
        for mapping in definition.findall("i3dMappings/i3dMapping")
    }

    def point(node_name: str):
        transform = _node_transform(scene, mappings.get(node_name, node_name))
        return transform[1]

    name = building_name(definition, building_file, mod, files)
    category = (definition.findtext("storeData/category") or "").strip()

    return (
        name,
        category,
        [
            tuple(point(area.get(key, "")) for key in ("startNode", "widthNode", "heightNode"))
            for area in indoor_areas
        ],
    )


def category_label(category: str) -> str:
    """A shop category in words: "sheds" → "Vehicle sheds"."""

    if not category:
        return tr("Other")

    labels = {
        "sheds": tr("Vehicle sheds"),
        "gardensheds": tr("Garden sheds"),
        "productionpoints": tr("Production points"),
        "sellingpoints": tr("Selling points"),
        "animalpens": tr("Animal pens"),
        "silos": tr("Silos"),
        "storages": tr("Storages"),
        "farmhouses": tr("Farmhouses"),
        "decoration": tr("Decoration"),
        "beehives": tr("Beehives"),
        "watertanks": tr("Water tanks"),
        "greenhouses": tr("Greenhouses"),
        "placeablemisc": tr("Miscellaneous"),
        "misc": tr("Miscellaneous"),
    }

    return labels.get(category.lower()) or _words(category)


def building_name(definition, building_file: str, mod: str | None, files: GameFiles) -> str:
    """The name of a building in the editor's language, see the module description."""

    element = definition.find("storeData/name")

    if element is None:
        return _words(Path(building_file).stem)

    # <name><en>Shed</en><de>Halle</de></name>
    if len(element):
        return _in_language(element)

    text = (element.text or "").strip()

    if not text.startswith(L10N_PREFIX):
        return text

    key = text.removeprefix(L10N_PREFIX)

    if mod is not None:
        try:
            translated = _mod_text(key, mod, files)
        except READ_ERRORS as error:
            logger.warning("Translations of %s could not be read: %s", mod, error)
            translated = None

        if translated:
            return translated

    return _words(key)


def _mod_text(key: str, mod: str, files: GameFiles) -> str | None:
    l10n = ET.fromstring(files.read(mod, "modDesc.xml")).find("l10n")

    if l10n is None:
        return None

    prefix = l10n.get("filenamePrefix")

    if prefix is None:
        texts = [text for text in l10n.findall("text") if text.get("name") == key]
        return _in_language(texts[0]) if texts else None

    for language in (current_language(), ENGLISH):
        try:
            translations = ET.fromstring(files.read(mod, f"{prefix}_{language}.xml"))
        except FileNotFoundError:
            continue

        for text in translations.iter("text"):
            if text.get("name") == key:
                return text.get("text")

    return None


def _in_language(element) -> str:
    return (element.findtext(current_language()) or element.findtext(ENGLISH) or "").strip()


def _words(key: str) -> str:
    """A translation key in words: "storeItem_mapUS_farmBarn" → "Farm barn"."""

    words = re.findall(r"[A-Z]+(?![a-z])|[A-Z]?[a-z]+|\d+", KEY_PREFIX.sub("", key))

    if not words:
        return key

    # Abbreviations like "BGA" keep their capitals.
    text = " ".join(word if word.isupper() else word.lower() for word in words)

    return text[0].upper() + text[1:]


def _node_transform(scene, node_path: str) -> Transform:
    """Transform of a scene node relative to its component, from a path like "0>2|0". The
    component's own transform is replaced by the building's placement."""

    component, _, children = node_path.partition(">")
    element = list(scene)[int(component)]
    transform = IDENTITY

    for index in filter(None, children.split("|")):
        element = list(element)[int(index)]
        transform = _combine(transform, _local_transform(element))

    return transform


def _local_transform(element) -> Transform:
    matrix = _rotation_matrix(_floats(element.get("rotation", "0 0 0")))
    scale = _floats(element.get("scale", "1 1 1"))
    scaled = tuple(tuple(row[i] * scale[i] for i in range(3)) for row in matrix)

    return scaled, _floats(element.get("translation", "0 0 0"))


def _rotation_matrix(degrees) -> tuple[tuple[float, ...], ...]:
    """Rotation by Euler angles in degrees, applied in the order X, Y, Z. Buildings are only turned
    around Y; X and Z are 0 or ±180, which gives the same result in any order."""

    cx, cy, cz = (math.cos(math.radians(angle)) for angle in degrees)
    sx, sy, sz = (math.sin(math.radians(angle)) for angle in degrees)

    rx = ((1, 0, 0), (0, cx, -sx), (0, sx, cx))
    ry = ((cy, 0, sy), (0, 1, 0), (-sy, 0, cy))
    rz = ((cz, -sz, 0), (sz, cz, 0), (0, 0, 1))

    return _multiply(rz, _multiply(ry, rx))


def _multiply(a, b) -> tuple[tuple[float, ...], ...]:
    return tuple(
        tuple(sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)) for i in range(3)
    )


def _apply(transform: Transform, point) -> tuple[float, float, float]:
    matrix, translation = transform

    return tuple(sum(matrix[i][k] * point[k] for k in range(3)) + translation[i] for i in range(3))


def _combine(outer: Transform, inner: Transform) -> Transform:
    """The transform that applies inner first, then outer."""

    return _multiply(outer[0], inner[0]), _apply(outer, inner[1])


def _floats(text: str) -> tuple[float, float, float]:
    x, y, z = (float(value) for value in text.split())

    return x, y, z
