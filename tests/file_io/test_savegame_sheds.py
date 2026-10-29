import zipfile

import pytest

from autodrive_editor.file_io.game_files import GameFiles
from autodrive_editor.file_io.savegame_sheds import category_label, read_preplaced, read_sheds

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


def test_buildings_without_indoor_area_are_left_out(game):
    silo = placeable(file="data/placeables/shed/silo.xml", unique_id="s")

    areas, failed = sheds(game, silo, placeable())

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


# The building node "m" lies in a group moved to (100 80 200); its ReferenceNode is turned by 90°.
# The second building "gone" is not in the savegame, e.g. because it was sold and torn down.
MAP_I3D = """<i3D><Files><File fileId="1" filename="shed.i3d"/></Files><Scene>
    <TransformGroup name="buildings" translation="100 80 200" nodeId="1">
        <TransformGroup name="preplaced_shed" nodeId="2">
            <TransformGroup name="placeable" nodeId="3">
                <ReferenceNode name="shed" rotation="0 90 0" referenceId="1" nodeId="4"/>
                <ReferenceNode name="other" translation="9 0 9" referenceId="1" nodeId="5"/>
            </TransformGroup>
        </TransformGroup>
        <TransformGroup name="preplaced_gone" translation="50 0 0" nodeId="6"/>
    </TransformGroup>
</Scene><UserAttributes>
    <UserAttribute nodeId="2">
        <Attribute name="onCreate" type="scriptCallback" value="Placeable.onCreate"/>
        <Attribute name="uniqueId" type="string" value="m"/>
        <Attribute name="xmlFilename" type="string" value="{file}"/>
    </UserAttribute>
    <UserAttribute nodeId="6">
        <Attribute name="onCreate" type="scriptCallback" value="Placeable.onCreate"/>
        <Attribute name="uniqueId" type="string" value="gone"/>
        <Attribute name="xmlFilename" type="string" value="{file}"/>
    </UserAttribute>
</UserAttributes></i3D>"""

CAREER = "<careerSavegame><settings><mapId>{}</mapId></settings></careerSavegame>"
PREPLACED = '<placeable isPreplaced="true" uniqueId="m"/>'
# The area of the turned shed, as in test_area_turns_with_the_building.
TURNED_CORNERS = [(92.5, 214), (92.5, 184), (107.5, 184), (107.5, 214)]


def base_game_map(game, file="$data/placeables/shed/shed.xml"):
    folder = game / "game/data/maps/mapUS"
    folder.mkdir(parents=True)
    (folder / "mapUS.xml").write_text(
        "<map><filename>$data/maps/mapUS/mapUS.i3d</filename></map>", encoding="utf-8"
    )
    (folder / "mapUS.i3d").write_text(MAP_I3D.format(file=file), encoding="utf-8")
    (game / "savegame1/careerSavegame.xml").write_text(CAREER.format("MapUS"), encoding="utf-8")


def test_map_building_is_placed_at_its_reference_node(game):
    base_game_map(game)

    areas, failed = sheds(game, PREPLACED)

    assert failed == []
    assert [area.unique_id for area in areas] == ["m"]
    assert rounded(areas[0].corners) == TURNED_CORNERS
    assert areas[0].height == 80
    assert areas[0].building_file == "$data/placeables/shed/shed.xml"


def test_map_buildings_missing_in_the_savegame_are_left_out(game):
    base_game_map(game)

    areas, _ = sheds(game, PREPLACED.replace('"m"', '"gone"'), '<placeable isPreplaced="true"/>')

    assert [area.unique_id for area in areas] == ["gone"]


def test_mod_map_is_found_by_its_map_id(game):
    mods = game / "mods"
    mods.mkdir()
    with zipfile.ZipFile(mods / "FS25_Map.zip", "w") as mod:
        mod.writestr(
            "modDesc.xml",
            '<modDesc><maps><map id="Other"/><map id="Sample" configFilename='
            '"maps/config/map.xml"/></maps></modDesc>',
        )
        mod.writestr("maps/config/map.xml", "<map><filename>maps/map.i3d</filename></map>")
        mod.writestr("maps/map.i3d", MAP_I3D.format(file="$data/placeables/shed/shed.xml"))
    (game / "savegame1/careerSavegame.xml").write_text(
        CAREER.format("FS25_Map.Sample"), encoding="utf-8"
    )

    areas, failed = sheds(game, PREPLACED)

    assert failed == []
    assert rounded(areas[0].corners) == TURNED_CORNERS


def test_unreadable_map_is_reported_and_placed_buildings_are_still_read(game):
    (game / "savegame1/careerSavegame.xml").write_text(CAREER.format("MapXX"), encoding="utf-8")

    areas, failed = sheds(game, PREPLACED, placeable())

    assert [area.unique_id for area in areas] == ["a"]
    assert failed == [str(game / "savegame1/careerSavegame.xml")]


def test_building_without_reference_node_is_placed_at_its_own_node():
    preplaced = read_preplaced(MAP_I3D.format(file="shed.xml").encode())

    assert preplaced["gone"][0] == "shed.xml"
    assert preplaced["gone"][1][1] == (150, 80, 200)


def test_scene_without_user_attributes_has_no_buildings():
    assert read_preplaced(b"<i3D><Scene/></i3D>") == {}


def named_shed(game, name, mod_files=None):
    """The shed of a building with the given storeData name, from a mod if mod_files are given."""

    definition = SHED_XML.replace("<base>", f"<storeData><name>{name}</name></storeData><base>")

    if mod_files is None:
        (game / "game/data/placeables/shed/shed.xml").write_text(definition, encoding="utf-8")
        areas, _ = sheds(game, placeable())
    else:
        (game / "mods").mkdir()
        with zipfile.ZipFile(game / "mods/FS25_Shed.zip", "w") as mod:
            mod.writestr("shed.xml", definition.replace("$data/placeables/shed/", ""))
            mod.writestr("shed.i3d", SHED_I3D)
            for path, text in mod_files.items():
                mod.writestr(path, text)
        areas, _ = sheds(game, placeable(file="$moddir$FS25_Shed/shed.xml"))

    return areas[0].name


@pytest.mark.parametrize(
    ("key", "name"),
    [
        ("$l10n_storeItem_mapUS_farmBarn", "Farm barn"),
        ("$l10n_storeItem_easyShed01", "Easy shed 01"),
        ("$l10n_shopItem_BGARamp", "BGA ramp"),
        ("Plain name", "Plain name"),
    ],
)
def test_base_game_name_is_the_key_in_words(game, key, name):
    assert named_shed(game, key) == name


def test_name_in_languages_uses_the_editor_language(game, german):
    assert named_shed(game, "<en>Shed</en><de>Halle</de>") == "Halle"


def test_building_without_name_is_named_by_its_file(game):
    assert sheds(game, placeable())[0][0].name == "Shed"


def test_mod_name_is_translated_in_its_mod_description(game):
    mod_desc = '<modDesc><l10n><text name="bigShed"><en>Big shed</en></text></l10n></modDesc>'

    assert named_shed(game, "$l10n_bigShed", {"modDesc.xml": mod_desc}) == "Big shed"


def test_mod_name_is_translated_in_its_translation_files(game, german):
    files = {
        "modDesc.xml": '<modDesc><l10n filenamePrefix="l10n/text"/></modDesc>',
        "l10n/text_de.xml": '<l10n><texts><text name="bigShed" text="Große Halle"/></texts></l10n>',
    }

    assert named_shed(game, "$l10n_bigShed", files) == "Große Halle"


def test_mod_name_without_translation_is_the_key_in_words(game):
    mod_desc = '<modDesc><l10n filenamePrefix="l10n/text"/></modDesc>'

    assert named_shed(game, "$l10n_bigShed", {"modDesc.xml": mod_desc}) == "Big shed"


def test_category_is_read_from_the_store_data(game):
    definition = SHED_XML.replace(
        "<base>", "<storeData><category>sheds</category></storeData><base>"
    )
    (game / "game/data/placeables/shed/shed.xml").write_text(definition, encoding="utf-8")

    areas, _ = sheds(game, placeable())

    assert areas[0].category == "sheds"
    assert areas[0].category_label == "Vehicle sheds"


@pytest.mark.parametrize(
    ("category", "label"),
    [("beeHives", "Beehives"), ("someNewCategory", "Some new category"), ("", "Other")],
)
def test_category_label(category, label):
    assert category_label(category) == label


def test_category_label_is_translated(german):
    assert category_label("sheds") == "Fahrzeughallen"
