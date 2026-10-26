from datetime import datetime

from autodrive_editor.editing.commands.delete_nodes import DeleteNodesCommand
from autodrive_editor.editing.commands.markers import AddMarkerCommand
from autodrive_editor.file_io.autodrive_xml import AutoDriveXmlReader
from autodrive_editor.file_io.autodrive_xml_writer import save_config
from autodrive_editor.file_io.routes_index import mark_route_saved, read_routes_index

SAVEGAME = """<?xml version="1.0" encoding="utf-8" standalone="no"?>
<AutoDrive>
    <version>3.0.1.4</version>
    <MapName>LS25_Test</MapName>
    <driverWages>2.000000</driverWages>
    <waypoints>
        <id>1,2,3</id>
        <x>0.000,10.000,20.000</x>
        <y>1.000,1.000,1.000</y>
        <z>0.000,0.000,0.000</z>
        <out>2;3;-1</out>
        <incoming>-1;1;2</incoming>
    </waypoints>
    <mapmarker>
        <mm1><id>3.000000</id><name>Silo</name><group>All</group></mm1>
        <mm2><id>1.000000</id><name>Hof</name><group>Felder</group></mm2>
    </mapmarker>
</AutoDrive>
"""


def round_trip(path):
    loaded = AutoDriveXmlReader.read(path)
    save_config(loaded.data, loaded.source)
    return AutoDriveXmlReader.load(path)


def node_tuples(data):
    return [
        (n.node_id, n.x, n.y, n.z, n.flag, n.outgoing, n.incoming) for n in data.get_sorted_nodes()
    ]


def test_unchanged_route_reads_back_the_same(write_xml):
    path = write_xml(
        x="0.5;10;20",
        y="1;2;3",
        z="-4;5;6",
        out="2,3;3;",
        incoming=";1;1,2",
        flags="0;2;4",
        markers='<m i="2" n="Hof" g="All"/><m i="1" n="Feld" g="Felder"/>',
        groups='<g n="Felder" i="7"/><g n="All" i="1"/>',
    )
    before = AutoDriveXmlReader.load(path)

    after = round_trip(path)

    assert node_tuples(after) == node_tuples(before)
    assert [(m.node_id, m.name, m.group) for m in after.markers.values()] == [
        (2, "Hof", "All"),
        (1, "Feld", "Felder"),
    ]
    assert [(g.name, g.group_id) for g in after.marker_groups] == [("Felder", 7), ("All", 1)]


def test_unchanged_savegame_reads_back_the_same(tmp_path):
    path = tmp_path / "AutoDrive_config.xml"
    path.write_text(SAVEGAME, encoding="utf-8")
    before = AutoDriveXmlReader.load(path)

    after = round_trip(path)

    assert node_tuples(after) == node_tuples(before)
    assert [(m.node_id, m.name, m.group) for m in after.markers.values()] == [
        (3, "Silo", "All"),
        (1, "Hof", "Felder"),
    ]


def test_route_uses_two_decimals_and_counts_waypoints(write_xml):
    path = write_xml(x="1.23456;2;3")

    round_trip(path)

    text = path.read_text(encoding="utf-8-sig")
    assert '<waypoints c="3">' in text
    assert "<x>1.23;2.00;3.00</x>" in text
    assert "<out>2;3;-1</out>" in text


def test_savegame_keeps_settings_and_adds_missing_flags(tmp_path):
    path = tmp_path / "AutoDrive_config.xml"
    path.write_text(SAVEGAME, encoding="utf-8")

    round_trip(path)

    text = path.read_text(encoding="utf-8-sig")
    assert "<driverWages>2.000000</driverWages>" in text
    assert "<MapName>LS25_Test</MapName>" in text
    assert "<x>0.000,10.000,20.000</x>" in text
    assert "<flags>0,0,0</flags>" in text
    assert "<mm2>\n            <id>1.000000</id>\n            <name>Hof</name>" in text


def test_file_is_written_like_the_game_does(write_xml):
    path = write_xml()

    round_trip(path)

    raw = path.read_bytes()
    assert raw.startswith(b'\xef\xbb\xbf<?xml version="1.0" encoding="utf-8" standalone="no"?>\r\n')
    assert b"\n" not in raw.replace(b"\r\n", b"")


def test_gaps_from_deleted_nodes_are_closed(write_xml):
    # 1 -> 2 -> 3 -> 4, marker on node 4.
    path = write_xml(
        x="0;10;20;30",
        y="0;0;0;0",
        z="0;0;0;0",
        out="2;3;4;",
        incoming=";1;2;3",
        flags="0;0;1;0",
        markers='<m i="4" n="Hof" g="All"/>',
        groups='<g n="All" i="1"/>',
    )
    loaded = AutoDriveXmlReader.read(path)
    DeleteNodesCommand(loaded.data, {2}).apply()

    save_config(loaded.data, loaded.source)
    data = AutoDriveXmlReader.load(path)

    assert [(n.node_id, n.x, n.flag) for n in data.get_sorted_nodes()] == [
        (1, 0, 0),
        (2, 20, 1),
        (3, 30, 0),
    ]
    assert data.get_node(1).outgoing == set()
    assert data.get_node(2).outgoing == {3}
    assert data.get_node(3).incoming == {2}
    assert list(data.markers) == [3]


def test_new_marker_group_gets_the_next_id(write_xml):
    path = write_xml(markers='<m i="1" n="Hof" g="All"/>', groups='<g n="All" i="4"/>')
    loaded = AutoDriveXmlReader.read(path)
    AddMarkerCommand(loaded.data, 2, "Feld", "Felder").apply()

    save_config(loaded.data, loaded.source)

    groups = AutoDriveXmlReader.load(path).marker_groups
    assert [(g.name, g.group_id) for g in groups] == [("All", 4), ("Felder", 5)]


def test_saved_route_gets_a_new_revision_in_routes_xml(tmp_path):
    (tmp_path / "routes").mkdir()
    route_file = tmp_path / "routes" / "abc.xml"
    (tmp_path / "routes.xml").write_text(
        '<autoDriveRoutesManager><routes><route name="A" fileName="abc.xml" map="M" '
        'revision="6" date="2025/04/15 19:53:11"><serverId></serverId></route>'
        '<route name="B" fileName="other.xml" map="M" revision="2" date="x"/>'
        "</routes></autoDriveRoutesManager>",
        encoding="utf-8",
    )

    assert mark_route_saved(route_file, datetime(2026, 10, 26, 9, 5, 7))

    entries = read_routes_index(tmp_path / "routes.xml")
    assert [(e.name, e.revision, e.date) for e in entries] == [
        ("A", 7, "2026/10/26 09:05:07"),
        ("B", 2, "x"),
    ]


def test_route_not_in_routes_xml_is_not_marked(tmp_path):
    (tmp_path / "routes.xml").write_text("<autoDriveRoutesManager/>", encoding="utf-8")

    assert not mark_route_saved(tmp_path / "routes" / "abc_autosave_1.xml", datetime.now())
