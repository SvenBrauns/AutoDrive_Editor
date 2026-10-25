"""Loads the map image shown under the AutoDrive network.

A map's overview.dds shows the map in its middle half; the outer border
holds decoration (a frame, a background picture, the map logo). The
editor cuts the middle half out and works with a 2048 px image, which
the background then scales to the map size.

Map images imported from mods are stored already cut out as PNG, so
they are loaded unchanged.
"""

import io
from pathlib import Path

from PIL import Image
from PySide6.QtGui import QImage, QPixmap

# Width and height of the background image at map scale 1 (2048 m).
MAP_IMAGE_SIZE = 2048


def crop_map_area(image: Image.Image) -> Image.Image:
    """The middle half of an overview image, scaled to MAP_IMAGE_SIZE."""

    image = image.convert("RGBA")
    width, height = image.size

    map_area = image.crop((width // 4, height // 4, width * 3 // 4, height * 3 // 4))

    if map_area.size != (MAP_IMAGE_SIZE, MAP_IMAGE_SIZE):
        map_area = map_area.resize((MAP_IMAGE_SIZE, MAP_IMAGE_SIZE), Image.Resampling.LANCZOS)

    return map_area


def map_image_from_dds_bytes(data: bytes) -> Image.Image:
    """Decodes an overview.dds read from a mod and cuts out the map."""

    return crop_map_area(Image.open(io.BytesIO(data)))


def load_background_pixmap(file_path) -> QPixmap:
    """overview.dds files are cut to the map area; other images (the PNGs
    in the map cache) are used as they are."""

    image = Image.open(file_path)

    if Path(file_path).suffix.lower() == ".dds":
        image = crop_map_area(image)
    else:
        image = image.convert("RGBA")

    width, height = image.size
    data = image.tobytes("raw", "RGBA")

    # copy() detaches the QImage from the Python bytes object.
    qimage = QImage(data, width, height, QImage.Format.Format_RGBA8888).copy()

    return QPixmap.fromImage(qimage)
