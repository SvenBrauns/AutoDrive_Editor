"""The indoor areas of the buildings in the loaded or linked savegame are shown as sheds."""

import pytest
from game_folder_helpers import add_routes, add_savegame, make_game_folder

MAP = "LS25_Test"

SHED_XML = """<placeable><base><filename>shed.i3d</filename></base>
    <indoorAreas>
        <indoorArea startNode="0>0|0" widthNode="0>0|0|0" heightNode="0>0|0|1"/>
    </indoorAreas>
</placeable>"""

SHED_I3D = """<i3D><Scene><TransformGroup><TransformGroup>
    <TransformGroup translation="-15 0 -7.5">
        <TransformGroup translation="30 0 0"/><TransformGroup translation="0 0 15"/>
    </TransformGroup>
</TransformGroup></TransformGroup></Scene></i3D>"""

PLACEABLE = '<placeable filename="{}" uniqueId="{}" position="0 80 0" rotation="0 0 0"/>'
PLACEABLES = (
    "<placeables>"
    + PLACEABLE.format("$moddir$FS25_Shed/shed.xml", "a")
    + PLACEABLE.format("$moddir$FS25_Missing/hall.xml", "b")
    + "</placeables>"
)


@pytest.fixture
def game(window, tmp_path):
    folder = make_game_folder(tmp_path / "FarmingSimulator2025")
    (folder / "mods/FS25_Shed").mkdir(parents=True)
    (folder / "mods/FS25_Shed/shed.xml").write_text(SHED_XML, encoding="utf-8")
    (folder / "mods/FS25_Shed/shed.i3d").write_text(SHED_I3D, encoding="utf-8")
    add_routes(folder, [("Hof", "route.xml", MAP, 1)])
    savegame = add_savegame(folder, 2, "Mein Hof", "LS25 Test", MAP)
    (savegame / "placeables.xml").write_text(PLACEABLES, encoding="utf-8")
    window.settings.set_game_folder(folder)
    window.route_path = folder / "modSettings/FS25_AutoDrive/routesManager/routes/route.xml"
    window.savegame = savegame
    return window


def shed_ids(window):
    return [area.unique_id for area in window.scene_renderer.shed_areas]


def test_loaded_savegame_shows_its_sheds_and_notes_unreadable_buildings(game):
    game.project_coordinator.load_xml_file(game.savegame / "AutoDrive_config.xml")

    assert shed_ids(game) == ["a"]
    assert game.status.text().endswith(" – 1 buildings could not be read (see log file)")


def test_route_shows_the_sheds_of_the_linked_savegame_only(game):
    coordinator = game.project_coordinator
    coordinator.load_xml_file(game.route_path)
    assert shed_ids(game) == []

    coordinator.set_savegame(game.savegame)
    assert shed_ids(game) == ["a"]

    coordinator.set_savegame(None)
    assert shed_ids(game) == []
