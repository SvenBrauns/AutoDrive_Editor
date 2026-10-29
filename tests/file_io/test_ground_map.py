import io

import pytest
from map_mod_helpers import make_single_map_mod, weight_png, write_map_mod
from PIL import Image

from autodrive_editor.file_io.ground_map import (
    SURFACE_COLORS,
    UNPAINTED_COLOR,
    Field,
    read_map_scene,
    render_ground_map,
    surface_group,
)
from autodrive_editor.file_io.mod_archive import ModArchive


@pytest.mark.parametrize(
    "name, group",
    [
        ("asphalt01", "asphalt"),
        ("asphaltGravel02", "asphalt"),
        ("concreteGravelSand01", "concrete"),
        ("gravelDirtMoss01", "gravel"),
        ("pebblesForestGround01", "gravel"),
        ("mudDarkGrassPatchy01", "mud"),
        ("animalMud01", "mud"),
        ("dirteu1", "mud"),
        ("forestGrass01", "forest"),
        ("rockyForestGround02", "rock"),
        ("sand01", "sand"),
        ("snow01", "other"),
    ],
)
def test_surface_group_is_the_earliest_keyword_in_the_name(name, group):
    assert surface_group(name) == group


def test_reads_weight_maps_and_fields_of_the_map_scene(tmp_path):
    with ModArchive(make_single_map_mod(tmp_path)) as archive:
        scene = read_map_scene(archive, "maps/map.i3d")

    # grass01 names a file that does not exist.
    assert scene.weight_maps == {"asphalt01": "maps/data/asphalt01_weight.png"}
    # Points add up the translations of the map, field and point groups.
    assert scene.fields == [Field(1, [(110.0, 220.0), (140.0, 220.0), (140.0, 250.0)])]


def test_field_numbers_follow_the_order_and_skip_groups_without_points(tmp_path):
    def field(name, points):
        return (
            f'<TransformGroup name="{name}"><TransformGroup name="polygonPoints">'
            + "".join(f'<TransformGroup name="p" translation="{p} 0 {p}"/>' for p in points)
            + "</TransformGroup></TransformGroup>"
        )

    i3d = (
        '<i3D><Scene><TransformGroup name="fields">'
        + field("a", [1, 2, 3])
        + field("b", [4, 5])
        + field("c", [6, 7, 8])
        + '</TransformGroup><TransformGroup name="other" translation="9 9 9"/></Scene></i3D>'
    )
    path = write_map_mod(tmp_path / "mod", {"map.i3d": i3d}, unpacked=True)

    with ModArchive(path) as archive:
        fields = read_map_scene(archive, "map.i3d").fields

    assert [(f.number, f.points[0]) for f in fields] == [(1, (1.0, 1.0)), (2, (6.0, 6.0))]


def test_label_position_is_the_mean_of_the_points():
    assert Field(1, [(0, 0), (30, 0), (30, 30), (0, 30)]).label_position == (15, 15)


def ground_archive(tmp_path, weights: dict[str, bytes]):
    files = {f"{name}.png": data for name, data in weights.items()}
    return ModArchive(write_map_mod(tmp_path / "mod", files, unpacked=True))


def two_halves(size=8):
    """Weight 200 in the left half, 0 in the right half."""

    image = Image.new("L", (size, size), 0)
    image.paste(200, (0, 0, size // 2, size))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_each_pixel_gets_the_color_of_the_strongest_group(tmp_path):
    weights = {
        "grass01": weight_png(8, 100),
        "asphalt01": two_halves(),
        "asphalt02": weight_png(8, 50),
    }

    with ground_archive(tmp_path, weights) as archive:
        image = render_ground_map(archive, {name: f"{name}.png" for name in weights})

    assert image.size == (8, 8)
    assert image.getpixel((0, 0)) == SURFACE_COLORS["asphalt"]
    assert image.getpixel((7, 0)) == SURFACE_COLORS["grass"]


def test_unpainted_pixels_and_maps_without_textures(tmp_path):
    with ground_archive(tmp_path, {"grass01": two_halves()}) as archive:
        image = render_ground_map(archive, {"grass01": "grass01.png"})
        assert render_ground_map(archive, {}) is None

    assert image.getpixel((7, 0)) == UNPAINTED_COLOR


def test_large_weight_maps_are_scaled_down(tmp_path):
    with ground_archive(
        tmp_path, {"grass01": weight_png(16), "sand01": weight_png(8, 1)}
    ) as archive:
        image = render_ground_map(
            archive, {"grass01": "grass01.png", "sand01": "sand01.png"}, max_size=8
        )

    assert image.size == (8, 8)
    assert image.getpixel((3, 3)) == SURFACE_COLORS["grass"]
