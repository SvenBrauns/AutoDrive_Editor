from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from PIL import Image


class HeightmapFormat(Enum):
    """Pixel formats a dem.png can have."""

    GRAYSCALE_8 = "8-Bit-Graustufen"
    GRAYSCALE_16 = "16-Bit-Graustufen"
    RGB_ENCODED_8 = "8-Bit-RGB-kodiert"


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
        return self.heightmap_format.value


def load_heightmap(file_path) -> HeightmapData:
    heightmap_path = Path(file_path).resolve()

    if not heightmap_path.is_file():
        raise FileNotFoundError(f"Die Heightmap wurde nicht gefunden: {heightmap_path}")

    try:
        with Image.open(heightmap_path) as source_image:
            if source_image.format != "PNG":
                raise ValueError("Die Heightmap muss eine PNG-Datei sein.")

            source_image.load()

            image = source_image.copy()

    except ValueError:
        raise

    except Exception as ex:
        raise ValueError(f"Die Heightmap konnte nicht geöffnet werden: {ex}") from ex

    if image.width <= 0 or image.height <= 0:
        raise ValueError("Die Heightmap besitzt eine ungültige Bildgröße.")

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
                "Die Integer-Heightmap enthält Werte außerhalb des unterstützten 16-Bit-Bereichs."
            )

        return HeightmapFormat.GRAYSCALE_16

    if image.mode in ("RGB", "RGBA"):
        return HeightmapFormat.RGB_ENCODED_8

    raise ValueError(f"Nicht unterstützter Heightmap-Bildmodus: {image.mode}")
