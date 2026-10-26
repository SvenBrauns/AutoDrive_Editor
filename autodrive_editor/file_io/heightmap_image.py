from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from PIL import Image

from autodrive_editor.i18n import tr


class HeightmapFormat(Enum):
    """Pixel formats a dem.png can have."""

    GRAYSCALE_8 = "grayscale_8"
    GRAYSCALE_16 = "grayscale_16"
    RGB_ENCODED_8 = "rgb_encoded_8"


@dataclass
class HeightmapData:
    """A loaded heightmap image and its detected format."""

    file_path: Path
    image: Image.Image
    heightmap_format: HeightmapFormat
    width: int
    height: int
    image_mode: str
    bands: tuple[str, ...]
    extrema: tuple

    @property
    def size(self) -> tuple[int, int]:
        return self.width, self.height

    @property
    def format_description(self) -> str:
        descriptions = {
            HeightmapFormat.GRAYSCALE_8: tr("8-bit grayscale"),
            HeightmapFormat.GRAYSCALE_16: tr("16-bit grayscale"),
            HeightmapFormat.RGB_ENCODED_8: tr("8-bit RGB encoded"),
        }

        return descriptions[self.heightmap_format]


def load_heightmap(file_path) -> HeightmapData:
    heightmap_path = Path(file_path).resolve()

    if not heightmap_path.is_file():
        raise FileNotFoundError(tr("The heightmap was not found: {path}", path=heightmap_path))

    try:
        with Image.open(heightmap_path) as source_image:
            if source_image.format != "PNG":
                raise ValueError(tr("The heightmap must be a PNG file."))

            source_image.load()

            image = source_image.copy()

    except ValueError:
        raise

    except Exception as ex:
        raise ValueError(tr("The heightmap could not be opened: {error}", error=ex)) from ex

    if image.width <= 0 or image.height <= 0:
        raise ValueError(tr("The heightmap has an invalid image size."))

    heightmap_format = _detect_heightmap_format(image)

    return HeightmapData(
        file_path=heightmap_path,
        image=image,
        heightmap_format=heightmap_format,
        width=image.width,
        height=image.height,
        image_mode=image.mode,
        bands=image.getbands(),
        extrema=image.getextrema(),
    )


def _detect_heightmap_format(image: Image.Image) -> HeightmapFormat:
    if image.mode == "L":
        return HeightmapFormat.GRAYSCALE_8

    if image.mode in ("I;16", "I;16L", "I;16B"):
        return HeightmapFormat.GRAYSCALE_16

    if image.mode == "I":
        minimum, maximum = image.getextrema()

        if minimum < 0 or maximum > 65535:
            raise ValueError(
                tr("The integer heightmap contains values outside the supported 16-bit range.")
            )

        return HeightmapFormat.GRAYSCALE_16

    if image.mode in ("RGB", "RGBA"):
        return HeightmapFormat.RGB_ENCODED_8

    raise ValueError(tr("Unsupported heightmap image mode: {mode}", mode=image.mode))
