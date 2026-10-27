"""Markers vehicles of a savegame park at get a parking sign."""

SAVEGAME = (
    "<AutoDrive><version>3.0.1.4</version><MapName>LS25_X</MapName>"
    "<waypoints><id>1,2</id><x>0,10</x><y>0,0</y><z>0,0</z>"
    "<out>2;-1</out><incoming>-1;1</incoming><flags>0,0</flags></waypoints>"
    "<mapmarker><mm1><id>1</id><name>A</name><group>All</group></mm1>"
    "<mm2><id>2</id><name>B</name><group>All</group></mm2></mapmarker></AutoDrive>"
)
VEHICLES = '<vehicles><vehicle><AutoDrive parkDestination="2"/></vehicle></vehicles>'


def parking_names(window):
    return [marker.name for marker in window.scene_renderer.parking_markers]


def test_savegame_shows_parking_at_the_numbered_marker(window, tmp_path):
    (tmp_path / "AutoDrive_config.xml").write_text(SAVEGAME, encoding="utf-8")
    (tmp_path / "vehicles.xml").write_text(VEHICLES, encoding="utf-8")

    window.project_coordinator.load_xml_file(tmp_path / "AutoDrive_config.xml")

    assert parking_names(window) == ["B"]


def test_route_has_no_parking(loaded_window):
    assert parking_names(loaded_window) == []
