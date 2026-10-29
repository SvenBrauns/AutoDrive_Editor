"""Small fake map mods for tests."""

import io
import zipfile

from PIL import Image

# The overview's middle half is the map; a frame colour around it shows
# whether the crop worked.
FRAME_COLOR = (0, 0, 255, 255)
MAP_COLOR = (0, 160, 0, 255)


def overview_dds(size=64) -> bytes:
    image = Image.new("RGBA", (size, size), FRAME_COLOR)
    image.paste(Image.new("RGBA", (size // 2, size // 2), MAP_COLOR), (size // 4, size // 4))
    buffer = io.BytesIO()
    image.save(buffer, format="DDS")
    return buffer.getvalue()


def heightmap_png(size=33) -> bytes:
    image = Image.new("I;16", (size, size))
    image.putdata([column * 100 for row in range(size) for column in range(size)])
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def weight_png(size=16, value=255) -> bytes:
    buffer = io.BytesIO()
    Image.new("L", (size, size), value).save(buffer, format="PNG")
    return buffer.getvalue()


TERRAIN_LAYERS = (
    '<TerrainTransformGroup name="terrain"><Layers>'
    '<Layer name="asphalt01" weightMapId="3"/><Layer name="grass01" weightMapId="99"/>'
    "</Layers></TerrainTransformGroup>"
)

# One field whose points are relative to the field and the group around it.
FIELDS = (
    '<TransformGroup name="map" translation="100 0 200"><TransformGroup name="fields">'
    '<TransformGroup name="field1" translation="10 5 20"><TransformGroup name="polygonPoints">'
    '<TransformGroup name="point1" translation="0 0 0"/>'
    '<TransformGroup name="point2" translation="30 0 0"/>'
    '<TransformGroup name="point3" translation="30 0 30"/>'
    '</TransformGroup><TransformGroup name="nameIndicator" translation="15 0 15"/>'
    "</TransformGroup></TransformGroup></TransformGroup>"
)


def map_files(folder="maps", title="LS25 Testkarte 2.0", width=4096, data_folder="data"):
    """Files of one map inside a mod."""

    return {
        f"{folder}/config/map.xml": (
            f'<map width="{width}" height="{width}" imageFilename="{folder}/overview.png">'
            f"<filename>{folder}/map.i3d</filename></map>"
        ),
        f"{folder}/map.i3d": (
            '<i3D><Files><File fileId="1" filename="textures/grass.png"/>'
            f'<File fileId="2" filename="{data_folder}/dem.png"/>'
            f'<File fileId="3" filename="{data_folder}/asphalt01_weight.png"/></Files>'
            f"<Scene>{TERRAIN_LAYERS}{FIELDS}</Scene></i3D>"
        ),
        f"{folder}/overview.dds": overview_dds(),
        f"{folder}/{data_folder}/dem.png": heightmap_png(),
        f"{folder}/{data_folder}/asphalt01_weight.png": weight_png(),
    }


def mod_desc(maps):
    """maps: list of (map id, config file, {language: title})."""

    entries = "".join(
        f'<map id="{map_id}" configFilename="{config}"><title>'
        + "".join(f"<{lang}>{text}</{lang}>" for lang, text in titles.items())
        + "</title></map>"
        for map_id, config, titles in maps
    )
    return f'<modDesc descVersion="100"><maps>{entries}</maps></modDesc>'


def write_map_mod(path, files: dict, unpacked=False):
    """Writes files as a zip, or as a folder when unpacked=True."""

    if unpacked:
        for name, content in files.items():
            target = path / name
            target.parent.mkdir(parents=True, exist_ok=True)
            data = content.encode("utf-8") if isinstance(content, str) else content
            target.write_bytes(data)
        return path

    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return path


def make_single_map_mod(directory, name="FS25_Testkarte", unpacked=False, **map_options):
    files = map_files(**map_options)
    title = map_options.get("title", "LS25 Testkarte 2.0")
    files["modDesc.xml"] = mod_desc([("SampleModMap", "maps/config/map.xml", {"de": title})])
    target = directory / name if unpacked else directory / f"{name}.zip"
    return write_map_mod(target, files, unpacked=unpacked)
