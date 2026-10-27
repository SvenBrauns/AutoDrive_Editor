import pytest
from PIL import Image

from autodrive_editor.terrain.heightmap import Heightmap

# Raw 16-bit value 0x8080 is the same height in every format: 8-bit 0x80 * 257,
# or red 0x80 and green 0x80.
HALF_HEIGHT = 0x8080 / 65535 * 255


def heightmap_file(tmp_path, mode, center, other):
    """3 × 3 heightmap with one value in the center pixel."""
    image = Image.new(mode, (3, 3), other)
    image.putpixel((1, 1), center)
    path = tmp_path / "dem.png"
    image.save(path)
    return path


@pytest.mark.parametrize(
    ("mode", "center", "other"),
    [("I;16", 0x8080, 0), ("L", 0x80, 0), ("RGB", (0x80, 0x80, 0), (0, 0, 0))],
    ids=["16 bit", "8 bit", "RGB encoded"],
)
def test_every_format_reads_the_same_height(tmp_path, mode, center, other):
    heightmap = Heightmap()
    heightmap.load(heightmap_file(tmp_path, mode, center, other))

    assert heightmap.get_height_at(0, 0, map_scale=1).height == pytest.approx(HALF_HEIGHT)


def test_map_corners_read_the_corner_pixels(tmp_path):
    heightmap = Heightmap()
    heightmap.load(heightmap_file(tmp_path, "I;16", 0, 0))

    # A 1x map is 2048 m wide and centered on 0.
    corner = heightmap.get_height_at(1024, -1024, map_scale=1)
    larger_map = heightmap.get_height_at(-2048, 2048, map_scale=2)

    assert (corner.pixel_x, corner.pixel_y) == (2, 0)
    assert (larger_map.pixel_x, larger_map.pixel_y) == (0, 2)


def test_positions_outside_the_map_are_refused(tmp_path):
    heightmap = Heightmap()
    heightmap.load(heightmap_file(tmp_path, "I;16", 0, 0))

    with pytest.raises(ValueError):
        heightmap.get_height_at(1025, 0, map_scale=1)


def test_only_png_files_are_accepted(tmp_path):
    path = tmp_path / "dem.png"
    Image.new("L", (3, 3)).save(path, format="BMP")

    with pytest.raises(ValueError):
        Heightmap().load(path)
