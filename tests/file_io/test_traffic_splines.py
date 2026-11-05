import pytest
from shapes_helpers import shapes_file, spline_data

from autodrive_editor.file_io.building_cache import BuildingCache
from autodrive_editor.file_io.game_files import GameFiles
from autodrive_editor.file_io.traffic_splines import map_traffic_lanes

SCENE = """<i3D><Shapes externalShapesFile="map.i3d.shapes"/><Scene>
<TransformGroup name="world" translation="100 0 0">
  <TransformGroup name="trafficSystem" nodeId="5" rotation="0 90 0">
    <TransformGroup scale="2 2 2"><Shape name="lane" shapeId="1" nodeId="7"/></TransformGroup>
    <Shape name="spawn" shapeId="2" nodeId="8"/>
  </TransformGroup>
</TransformGroup></Scene>
<UserAttributes>
  <UserAttribute nodeId="5">
    <Attribute name="onCreate" value="TrafficSystem.onCreate"/></UserAttribute>
  <UserAttribute nodeId="7"><Attribute name="speedLimit" value="50"/></UserAttribute>
  <UserAttribute nodeId="8"><Attribute name="isTeleport" value="true"/></UserAttribute>
</UserAttributes></i3D>"""


def make_map(tmp_path, scene):
    folder = tmp_path / "game/data/maps/mapTest"
    folder.mkdir(parents=True)
    (folder / "mapTest.xml").write_text(
        "<map><filename>data/maps/mapTest/map.i3d</filename></map>", encoding="utf-8"
    )
    (folder / "map.i3d").write_text(scene, encoding="utf-8")
    splines = [
        (2, spline_data("lane", 1, [(1, 0, 0), (0, 1, 3)])),
        (2, spline_data("s", 2, [(0, 0, 0)])),
    ]
    (folder / "map.i3d.shapes").write_bytes(shapes_file(splines))
    savegame = tmp_path / "savegame1"
    savegame.mkdir()
    (savegame / "careerSavegame.xml").write_text(
        "<careerSavegame><settings><mapId>MapTest</mapId></settings></careerSavegame>",
        encoding="utf-8",
    )
    return savegame


def test_lanes_are_placed_through_the_nested_groups_without_spawn_splines(tmp_path):
    savegame = make_map(tmp_path, SCENE)

    with GameFiles(tmp_path / "game", None) as files:
        lanes = map_traffic_lanes(savegame, files)

    assert len(lanes) == 1
    assert lanes[0].speed_limit == 50
    # Scaled by 2, turned 90° around y, moved by the outer group.
    assert lanes[0].points == (pytest.approx((100, 0, -2)), pytest.approx((106, 2, 0)))


def test_lanes_are_kept_in_the_cache(tmp_path):
    savegame = make_map(tmp_path, SCENE)
    cache = BuildingCache()

    with GameFiles(tmp_path / "game", None) as files:
        first = map_traffic_lanes(savegame, files, cache)
        (tmp_path / "game/data/maps/mapTest/map.i3d.shapes").unlink()

        assert map_traffic_lanes(savegame, files, cache) == first


def test_a_map_without_traffic_system_has_no_lanes(tmp_path):
    savegame = make_map(tmp_path, SCENE.replace("TrafficSystem.onCreate", "Other.onCreate"))
    (tmp_path / "game/data/maps/mapTest/map.i3d.shapes").unlink()

    with GameFiles(tmp_path / "game", None) as files:
        assert map_traffic_lanes(savegame, files) == []
