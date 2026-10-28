"""Indoor areas of the buildings placed in a savegame, used as sheds.

    placeables.xml
        <placeable filename="data/placeables/easySheds/easyShed01/easyShed01.xml"
            uniqueId="…" position="-354.456 84.894 1207.828" rotation="0.00 -38.34 0.00">

    easyShed01.xml  (building definition)
        <base><filename>$data/placeables/easySheds/easyShed01/easyShed01.i3d</filename></base>
        <indoorAreas><indoorArea startNode="indoorAreaStart01" widthNode="…" heightNode="…"/>
        <i3dMappings><i3dMapping id="indoorAreaStart01" node="0>2|0"/>

    easyShed01.i3d  (scene; "0>2|0" is child 0 of child 2 of the first component)
        <TransformGroup name="indoorAreaStart01" translation="-15 0 -7.5">
            <TransformGroup name="indoorAreaWidth01" translation="30 0 0"/>
            <TransformGroup name="indoorAreaHeight01" translation="0 0 15"/>

Map-preplaced buildings have no position in placeables.xml and are left out.
"""

import math
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass
from pathlib import Path

from autodrive_editor.error_log import logger
from autodrive_editor.file_io.game_files import GameFiles, locate

# 3 × 3 matrix and translation: point → matrix · point + translation.
Transform = tuple[tuple[tuple[float, ...], ...], tuple[float, float, float]]

IDENTITY: Transform = (((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)), (0.0, 0.0, 0.0))

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

    # Indoor areas in building coordinates, by building file; None if it could not be read.
    building_areas: dict[str, list | None] = {}
    areas = []

    for placeable in placeables:
        building_file = placeable.get("filename", "")
        position = placeable.get("position")

        if not building_file or position is None:
            continue

        if building_file not in building_areas:
            try:
                building_areas[building_file] = read_building_areas(building_file, files)
            except READ_ERRORS as error:
                logger.warning("Building %s could not be read: %s", building_file, error)
                building_areas[building_file] = None

        local_areas = building_areas[building_file]

        if not local_areas:
            continue

        translation = _floats(position)
        placement = (_rotation_matrix(_floats(placeable.get("rotation", "0 0 0"))), translation)

        for points in local_areas:
            start, width, height = (_apply(placement, point) for point in points)
            opposite = tuple(w + h - s for s, w, h in zip(start, width, height, strict=True))

            areas.append(
                IndoorArea(
                    building_file=building_file,
                    unique_id=placeable.get("uniqueId", ""),
                    corners=tuple((p[0], p[2]) for p in (start, width, opposite, height)),
                    height=translation[1],
                )
            )

    failed = [name for name, local_areas in building_areas.items() if local_areas is None]

    return areas, failed


def read_building_areas(building_file: str, files: GameFiles) -> list:
    """The indoor areas of a building definition as (start, width, height) points relative to the
    building."""

    mod, path = locate(building_file)
    definition = ET.fromstring(files.read(mod, path))
    indoor_areas = definition.findall("indoorAreas/indoorArea")

    if not indoor_areas:
        return []

    i3d_name = definition.findtext("base/filename") or definition.findtext("filename") or ""
    scene = ET.fromstring(files.read(*locate(i3d_name, mod))).find("Scene")

    mappings = {
        mapping.get("id"): mapping.get("node")
        for mapping in definition.findall("i3dMappings/i3dMapping")
    }

    def point(node_name: str):
        transform = _node_transform(scene, mappings.get(node_name, node_name))
        return transform[1]

    return [
        tuple(point(area.get(key, "")) for key in ("startNode", "widthNode", "heightNode"))
        for area in indoor_areas
    ]


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
