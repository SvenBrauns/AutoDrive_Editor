"""A schematic map drawn from a map's ground textures, plus its field outlines.

    map.i3d
        <File fileId="4" filename="data/asphalt01_weight.png"/>
        <TerrainTransformGroup name="terrain">
            <Layers><Layer name="asphalt01" weightMapId="4" …/></Layers>
        </TerrainTransformGroup>
        <TransformGroup name="fields">
            <TransformGroup name="field1" translation="-980 109 -987">
                <TransformGroup name="polygonPoints">
                    <TransformGroup name="point1" translation="0 0 187"/>

A weight map is a grayscale image (1 px per metre) of how strongly its
texture is painted. Each pixel of the ground map gets the colour of the
surface group whose texture is painted strongest there. Field points are
relative to their parent groups; the groups' rotations are ignored. Field
numbers are the order of the fields in the group, as in the game.
"""

import io
import posixpath
import xml.etree.ElementTree as ET
from dataclasses import dataclass

from PIL import Image, ImageChops

from autodrive_editor.file_io.mod_archive import ModArchive

# The ground map of a larger map is scaled down to this size (2 m per pixel on a 16x map).
MAX_GROUND_MAP_SIZE = 4096

# Surface groups in the order a texture name is checked against; the
# earliest match in the name wins ("rockyForestGround" is rock).
SURFACE_KEYWORDS = {
    "asphalt": "asphalt",
    "concrete": "concrete",
    "gravel": "gravel",
    "pebble": "gravel",
    "grass": "grass",
    "mud": "mud",
    "dirt": "mud",
    "forest": "forest",
    "leaves": "forest",
    "needle": "forest",
    "rock": "rock",
    "sand": "sand",
}

SURFACE_COLORS = {
    "asphalt": (70, 70, 74),
    "concrete": (165, 165, 160),
    "gravel": (190, 170, 130),
    "grass": (110, 150, 80),
    "mud": (125, 95, 65),
    "forest": (60, 95, 55),
    "rock": (120, 125, 135),
    "sand": (215, 195, 140),
    "other": (150, 150, 140),
}

# Where no texture is painted at all.
UNPAINTED_COLOR = (40, 40, 40)


@dataclass(frozen=True)
class Field:
    number: int
    points: list[tuple[float, float]]

    @property
    def label_position(self) -> tuple[float, float]:
        xs, zs = zip(*self.points, strict=True)
        return sum(xs) / len(xs), sum(zs) / len(zs)


@dataclass(frozen=True)
class MapScene:
    # Texture name -> weight map path inside the mod.
    weight_maps: dict[str, str]
    fields: list[Field]


def surface_group(layer_name: str) -> str:
    """The surface group of a ground texture, by its name."""

    name = layer_name.lower()
    found = [(name.find(keyword), group) for keyword, group in SURFACE_KEYWORDS.items()]
    found = [(position, group) for position, group in found if position >= 0]

    return min(found)[1] if found else "other"


def resolve_i3d_path(archive: ModArchive, i3d_file: str, filename: str) -> str | None:
    """A file named in an i3d, relative to the i3d or ("$data/...") to the game's data folder."""

    if filename.startswith("$"):
        return archive.resolve(filename)

    return archive.resolve(
        posixpath.normpath(posixpath.join(posixpath.dirname(i3d_file), filename))
    )


def read_map_scene(archive: ModArchive, i3d_file: str) -> MapScene:
    """The ground textures with their weight maps and the field outlines of a map.i3d."""

    files: dict[str, str] = {}
    layers: dict[str, str] = {}
    fields: list[Field] = []

    # Per open element: its name and translation (x, z).
    stack: list[tuple[str, float, float]] = []
    fields_depth = None
    points: list[tuple[float, float]] | None = None

    with archive.open(i3d_file) as stream:
        for event, element in ET.iterparse(stream, events=("start", "end")):
            if event == "end":
                if element.tag == "TransformGroup":
                    stack.pop()

                    # A field group or the fields group itself has ended.
                    if points is not None and len(stack) == fields_depth:
                        if len(points) >= 3:
                            fields.append(Field(len(fields) + 1, points))
                        points = None
                    elif fields_depth is not None and len(stack) < fields_depth:
                        fields_depth = None

                element.clear()
                continue

            if element.tag == "File":
                files[element.get("fileId", "")] = element.get("filename", "")
            elif element.tag == "Layer" and element.get("weightMapId"):
                layers[element.get("name", "")] = element.get("weightMapId")
            elif element.tag == "TransformGroup":
                name = element.get("name", "")
                x, _, z = (float(value) for value in element.get("translation", "0 0 0").split())
                stack.append((name, x, z))

                if fields_depth is None and name == "fields" and not fields:
                    fields_depth = len(stack)
                elif fields_depth is not None and len(stack) == fields_depth + 1:
                    points = []
                elif points is not None and stack[-2][0] == "polygonPoints":
                    points.append(
                        (sum(entry[1] for entry in stack), sum(entry[2] for entry in stack))
                    )

    weight_maps = {
        name: path
        for name, file_id in layers.items()
        if (path := resolve_i3d_path(archive, i3d_file, files.get(file_id, ""))) is not None
    }

    return MapScene(weight_maps=weight_maps, fields=fields)


def render_ground_map(
    archive: ModArchive, weight_maps: dict[str, str], max_size: int = MAX_GROUND_MAP_SIZE
) -> Image.Image | None:
    """The ground map as an RGB image, or None if the map has no weight maps."""

    strongest: dict[str, Image.Image] = {}

    for name, path in weight_maps.items():
        weight = Image.open(io.BytesIO(archive.read(path))).convert("L")

        if weight.width > max_size:
            weight = weight.resize((max_size, max_size), Image.Resampling.BOX)

        group = surface_group(name)
        strongest[group] = (
            ImageChops.lighter(strongest[group], weight) if group in strongest else weight
        )

    if not strongest:
        return None

    size = max(image.size for image in strongest.values())
    image = Image.new("RGB", size, UNPAINTED_COLOR)
    best = Image.new("L", size, 0)

    for group, weight in strongest.items():
        weight = weight.resize(size) if weight.size != size else weight
        stronger = ImageChops.subtract(weight, best).point(lambda value: 255 if value else 0)
        image.paste(SURFACE_COLORS[group], mask=stronger)
        best = ImageChops.lighter(best, weight)

    return image
