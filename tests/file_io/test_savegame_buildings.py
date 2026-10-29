import pytest

from autodrive_editor.file_io.game_files import GameFiles
from autodrive_editor.file_io.savegame_buildings import BuildingGroup, read_savegame_buildings

I3D = """<i3D><Scene><TransformGroup>
    <TransformGroup name="a"><TransformGroup name="b"/><TransformGroup name="c"/></TransformGroup>
</TransformGroup></Scene></i3D>"""

AREAS = '<indoorAreas><indoorArea startNode="0>0" widthNode="0>0|0" heightNode="0>0|1"/>'
AREAS += "</indoorAreas>"
TRIGGER = '<sellingStation><unloadTrigger exactFillRootNode="0>0"/></sellingStation>'

DEFINITIONS = {
    "hall": AREAS,
    "mill": TRIGGER,
    "bunker": "<bunkerSilo/>",
    "mill_with_hall": TRIGGER + AREAS,
    "bunker_with_trigger": "<bunkerSilo/>" + TRIGGER,
    "fence": "",
    "house": AREAS,
}


@pytest.fixture
def buildings(tmp_path):
    folder = tmp_path / "game/data/placeables"
    folder.mkdir(parents=True)
    (folder / "building.i3d").write_text(I3D, encoding="utf-8")
    placeables = []

    for name, content in DEFINITIONS.items():
        category = "farmhouses" if name == "house" else "misc"
        definition = (
            f"<placeable><storeData><name>{name}</name><category>{category}</category></storeData>"
            f"<base><filename>$data/placeables/building.i3d</filename></base>{content}</placeable>"
        )
        (folder / f"{name}.xml").write_text(definition, encoding="utf-8")
        placeables.append(
            f'<placeable filename="data/placeables/{name}.xml" uniqueId="{name}" '
            'position="0 0 0" rotation="0 0 0"/>'
        )

    # A second mill.
    placeables.append(placeables[1].replace('uniqueId="mill"', 'uniqueId="mill2"'))
    (tmp_path / "savegame1").mkdir()
    (tmp_path / "savegame1/placeables.xml").write_text(
        f"<placeables>{''.join(placeables)}</placeables>", encoding="utf-8"
    )
    with GameFiles(tmp_path / "game", None) as files:
        return read_savegame_buildings(tmp_path / "savegame1", files)


def test_each_type_with_sheds_stations_or_a_bunker_silo_is_in_one_group(buildings):
    groups = {item.name: item.group for item in buildings.types}

    assert groups == {
        "hall": BuildingGroup.SHEDS,
        "mill": BuildingGroup.STATIONS,
        "bunker": BuildingGroup.BUNKER_SILOS,
        "mill_with_hall": BuildingGroup.STATIONS,
        "bunker_with_trigger": BuildingGroup.BUNKER_SILOS,
        # Only for the player's character.
        "house": BuildingGroup.OTHER,
    }


def test_types_are_counted_and_read_once(buildings):
    mill = next(item for item in buildings.types if item.name == "mill")

    assert mill.count == 2
    assert mill.category_label == "Miscellaneous"
    assert mill.building_file == "data/placeables/mill.xml"


def test_areas_and_stops_are_read_whatever_the_group(buildings):
    assert sorted(area.unique_id for area in buildings.areas) == ["hall", "house", "mill_with_hall"]
    assert sorted(stop.unique_id for stop in buildings.stops) == [
        "bunker_with_trigger",
        "mill",
        "mill2",
        "mill_with_hall",
    ]
    assert buildings.failed == []


def test_group_label_is_translated(german):
    assert BuildingGroup.BUNKER_SILOS.label == "Fahrsilos"
