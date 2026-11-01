"""The sheds and stations of the buildings in the loaded or linked savegame are shown."""

import pytest
from game_folder_helpers import add_routes, add_savegame, make_game_folder
from PySide6.QtCore import Qt

from autodrive_editor.file_io.savegame_buildings import BuildingGroup

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
    return [area.unique_id for area in window.scene_renderer.buildings.areas]


def test_loaded_savegame_shows_its_sheds_and_notes_unreadable_buildings(game):
    game.project_coordinator.load_xml_file(game.savegame / "AutoDrive_config.xml")

    assert shed_ids(game) == ["a"]
    assert game.status.text().endswith(" – 1 buildings could not be read (see log file)")


def test_route_opened_alone_shows_no_sheds(game):
    game.project_coordinator.load_xml_file(game.savegame / "AutoDrive_config.xml")
    game.project_coordinator.load_xml_file(game.route_path)

    assert shed_ids(game) == []


def test_building_types_are_remembered(game):
    game.project_coordinator.load_xml_file(game.savegame / "AutoDrive_config.xml")

    def change(dialog):
        dialog._check_all(Qt.CheckState.Unchecked)
        dialog.set_group(dialog._items()[0], BuildingGroup.STATIONS)
        return True

    game._run_dialog = change
    game.actions.building_types_action.trigger()

    assert game.settings.hidden_building_types == {"$moddir$FS25_Shed/shed.xml"}
    assert game.settings.building_groups == {"$moddir$FS25_Shed/shed.xml": BuildingGroup.STATIONS}
    assert game.scene_renderer.shown_shed_areas == []
    assert game.scene_renderer.group_of("$moddir$FS25_Shed/shed.xml") == BuildingGroup.STATIONS
