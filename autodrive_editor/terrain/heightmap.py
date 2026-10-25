from dataclasses import dataclass

from autodrive_editor.file_io.heightmap_image import HeightmapData, HeightmapFormat, load_heightmap
from autodrive_editor.terrain.heightmap_transform import HeightmapTransform


@dataclass(frozen=True)
class HeightSample:
    """The terrain height at a map position and the pixel it was read from."""

    world_x: float
    world_z: float

    pixel_x: int
    pixel_y: int

    raw_value: int
    normalized_value: float
    height: float


class Heightmap:
    """Reads terrain heights from a loaded dem.png."""

    DEFAULT_HEIGHT_SCALE = 255.0
    MAX_16_BIT_VALUE = 65535

    def __init__(self, height_scale=DEFAULT_HEIGHT_SCALE):
        self.height_scale = self._validate_height_scale(height_scale)

        self.heightmap_data = None

    @property
    def file_path(self):
        if self.heightmap_data is None:
            return None

        return self.heightmap_data.file_path

    @property
    def width(self):
        if self.heightmap_data is None:
            return None

        return self.heightmap_data.width

    @property
    def height(self):
        if self.heightmap_data is None:
            return None

        return self.heightmap_data.height

    @property
    def heightmap_format(self):
        if self.heightmap_data is None:
            return None

        return self.heightmap_data.heightmap_format

    @property
    def format_description(self):
        if self.heightmap_data is None:
            return None

        return self.heightmap_data.format_description

    def load(self, file_path):
        heightmap_data = load_heightmap(file_path)

        self.heightmap_data = heightmap_data

        return heightmap_data

    def clear(self):
        self.heightmap_data = None

    def has_heightmap(self):
        return self.heightmap_data is not None

    def set_height_scale(self, height_scale):
        self.height_scale = self._validate_height_scale(height_scale)

    def get_height_at(self, world_x, world_z, map_scale, clamp=False):
        heightmap_data = self._require_heightmap()

        pixel_x, pixel_y = HeightmapTransform.world_to_pixel(
            world_x=world_x,
            world_z=world_z,
            image_width=heightmap_data.width,
            image_height=heightmap_data.height,
            map_scale=map_scale,
            clamp=clamp,
        )

        raw_value = self._get_raw_value(heightmap_data, pixel_x, pixel_y)

        normalized_value = raw_value / self.MAX_16_BIT_VALUE

        height = normalized_value * self.height_scale

        return HeightSample(
            world_x=float(world_x),
            world_z=float(world_z),
            pixel_x=pixel_x,
            pixel_y=pixel_y,
            raw_value=raw_value,
            normalized_value=normalized_value,
            height=height,
        )

    def get_image_information(self):
        heightmap_data = self._require_heightmap()

        return {
            "file_path": str(heightmap_data.file_path),
            "format": (heightmap_data.format_description),
            "image_mode": (heightmap_data.image_mode),
            "width": heightmap_data.width,
            "height": heightmap_data.height,
            "bands": heightmap_data.bands,
            "extrema": heightmap_data.extrema,
            "height_scale": self.height_scale,
        }

    def _require_heightmap(self) -> HeightmapData:
        if self.heightmap_data is None:
            raise RuntimeError("Es wurde keine Heightmap geladen.")

        return self.heightmap_data

    def _get_raw_value(self, heightmap_data, pixel_x, pixel_y):
        pixel_value = heightmap_data.image.getpixel((pixel_x, pixel_y))

        if heightmap_data.heightmap_format == HeightmapFormat.GRAYSCALE_16:
            raw_value = int(pixel_value)

        elif heightmap_data.heightmap_format == HeightmapFormat.GRAYSCALE_8:
            raw_value = int(pixel_value) * 257

        elif heightmap_data.heightmap_format == HeightmapFormat.RGB_ENCODED_8:
            red = int(pixel_value[0])

            green = int(pixel_value[1])

            raw_value = (red << 8) + green

        else:
            raise ValueError("Das Heightmap-Format wird nicht unterstützt.")

        if raw_value < 0 or raw_value > self.MAX_16_BIT_VALUE:
            raise ValueError(f"Ungültiger Heightmap-Rohwert: {raw_value}")

        return raw_value

    @staticmethod
    def _validate_height_scale(height_scale):
        height_scale = float(height_scale)

        if height_scale <= 0:
            raise ValueError("Der Height-Scale muss größer als 0 sein.")

        return height_scale
