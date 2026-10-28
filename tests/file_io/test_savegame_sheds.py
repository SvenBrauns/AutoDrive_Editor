import pytest

from autodrive_editor.file_io.game_files import GameFiles
from autodrive_editor.file_io.savegame_sheds import read_sheds

SHED_XML = """<placeable>
    <base><filename>$data/placeables/shed/shed.i3d</filename></base>
    <indoorAreas><indoorArea startNode="start" widthNode="width" heightNode="height"/></indoorAreas>
    <i3dMappings>
        <i3dMapping id="start" node="0>1|0"/>
        <i3dMapping id="width" node="0>1|0|0"/>
        <i3dMapping id="height" node="0>1|0|1"/>
    </i3dMappings>
</placeable>"""

# A 30 × 15 m area under a group moved by 1 m along x.
SHED_I3D = """<i3D><Scene><TransformGroup name="shed" translation="500 0 500">
    <TransformGroup name="other"/>
    <TransformGroup name="indoorAreas" translation="1 0 0">
        <TransformGroup name="start" translation="-15 0 -7.5">
            <TransformGroup name="width" translation="30 0 0"/>
            <TransformGroup name="height" translation="0 0 15"/>
        </TransformGroup>
    </TransformGroup>
</TransformGroup></Scene></i3D>"""

PLACEABLE = (
    '<placeable filename="{file}" uniqueId="{id}" position="100 80 200" rotation="{rotation}"/>'
)


@pytest.fixture
def game(tmp_path):
    shed = tmp_path / "game/data/placeables/shed"
    shed.mkdir(parents=True)
    (shed / "shed.xml").write_text(SHED_XML, encoding="utf-8")
    (shed / "shed.i3d").write_text(SHED_I3D, encoding="utf-8")
    (shed / "silo.xml").write_text("<placeable/>", encoding="utf-8")
    (tmp_path / "savegame1").mkdir()
    return tmp_path


def sheds(game, *placeables):
    (game / "savegame1/placeables.xml").write_text(
        f"<placeables>{''.join(placeables)}</placeables>", encoding="utf-8"
    )
    with GameFiles(game / "game", game / "mods") as files:
        return read_sheds(game / "savegame1", files)


def placeable(rotation="0 0 0", file="data/placeables/shed/shed.xml", unique_id="a"):
    return PLACEABLE.format(file=file, id=unique_id, rotation=rotation)


def rounded(corners):
    return [(round(x, 3), round(z, 3)) for x, z in corners]


def test_area_is_placed_at_the_building_position(game):
    areas, failed = sheds(game, placeable())

    assert failed == []
    assert len(areas) == 1
    assert rounded(areas[0].corners) == [(86, 192.5), (116, 192.5), (116, 207.5), (86, 207.5)]
    assert areas[0].height == 80
    assert areas[0].unique_id == "a"
    assert areas[0].building_file == "data/placeables/shed/shed.xml"


def test_area_turns_with_the_building(game):
    areas, _ = sheds(game, placeable(rotation="0 90 0"))

    # Turned by 90° around y: x → -z, z → x.
    assert rounded(areas[0].corners) == [(92.5, 214), (92.5, 184), (107.5, 184), (107.5, 214)]


def test_x_and_z_turned_by_180_degrees_is_a_turn_around_y(game):
    flipped, _ = sheds(game, placeable(rotation="-180 -30 180"))
    turned, _ = sheds(game, placeable(rotation="0 210 0"))

    assert rounded(flipped[0].corners) == rounded(turned[0].corners)


def test_preplaced_buildings_and_buildings_without_indoor_area_are_left_out(game):
    preplaced = '<placeable isPreplaced="true" uniqueId="p"/>'
    silo = placeable(file="data/placeables/shed/silo.xml", unique_id="s")

    areas, failed = sheds(game, preplaced, silo, placeable())

    assert [area.unique_id for area in areas] == ["a"]
    assert failed == []


def test_unreadable_buildings_are_reported_once(game):
    missing = placeable(file="$moddir$FS25_Missing/shed.xml")

    areas, failed = sheds(game, missing, missing, placeable())

    assert len(areas) == 1
    assert failed == ["$moddir$FS25_Missing/shed.xml"]


def test_savegame_without_placeables_has_no_sheds(tmp_path):
    with GameFiles(None, None) as files:
        assert read_sheds(tmp_path, files) == ([], [])
