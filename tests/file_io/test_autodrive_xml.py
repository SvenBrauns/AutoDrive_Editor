import pytest

from autodrive_editor.file_io.autodrive_xml import AutoDriveXmlReader, ConfigFormat


def test_loads_coordinates_with_one_based_ids(write_xml):
    path = write_xml(x="1.5;2.5", y="10;20", z="-3;-4", out="", incoming="", flags="")

    data = AutoDriveXmlReader.load(path)

    assert sorted(data.nodes) == [1, 2]
    node = data.get_node(2)
    assert (node.x, node.y, node.z) == (2.5, 20.0, -4.0)


def test_loads_connections_by_position(write_xml):
    # Node 1 -> 2, node 2 -> 1 and 3, node 3 has no outgoing connection.
    path = write_xml(out="2;1,3;", incoming="2;1;2")

    data = AutoDriveXmlReader.load(path)

    assert data.get_node(1).outgoing == {2}
    assert data.get_node(2).outgoing == {1, 3}
    assert data.get_node(3).outgoing == set()
    assert data.get_node(3).incoming == {2}


def test_ignores_non_positive_connection_ids(write_xml):
    path = write_xml(out="-1;0,1;2")

    data = AutoDriveXmlReader.load(path)

    assert data.get_node(1).outgoing == set()
    assert data.get_node(2).outgoing == {1}


def test_missing_connections_and_flags_default_to_empty(write_xml):
    path = write_xml(out=None, incoming=None, flags=None)

    data = AutoDriveXmlReader.load(path)

    for node in data.nodes.values():
        assert node.outgoing == set()
        assert node.incoming == set()
        assert node.flag == 0


def test_short_flag_list_is_padded_with_zero(write_xml):
    path = write_xml(flags="1")

    data = AutoDriveXmlReader.load(path)

    assert [data.get_node(i).flag for i in (1, 2, 3)] == [1, 0, 0]


def test_loads_markers_and_skips_invalid_ones(write_xml):
    markers = (
        '<mm1 i="1" n="Hof" g="All"/>'
        '<mm2 i="99" n="Unbekannt"/>'
        '<mm3 i="abc" n="Kaputt"/>'
        '<mm4 n="Ohne ID"/>'
    )
    path = write_xml(markers=markers)

    data = AutoDriveXmlReader.load(path)

    assert list(data.markers) == [1]
    assert data.get_marker(1).name == "Hof"
    assert data.get_marker(1).group == "All"


def test_missing_file_raises_file_not_found(tmp_path):
    with pytest.raises(FileNotFoundError):
        AutoDriveXmlReader.load(tmp_path / "missing.xml")


def test_malformed_xml_raises_value_error(write_xml):
    path = write_xml(raw="<AutoDrive><waypoints>")

    with pytest.raises(ValueError, match="invalid"):
        AutoDriveXmlReader.load(path)


def test_missing_waypoints_raises_value_error(write_xml):
    path = write_xml(raw="<routeExport></routeExport>")

    with pytest.raises(ValueError, match="waypoints"):
        AutoDriveXmlReader.load(path)


def test_missing_coordinate_element_raises_value_error(write_xml):
    path = write_xml(raw="<routeExport><waypoints><x>1</x><y>1</y></waypoints></routeExport>")

    with pytest.raises(ValueError, match="z coordinates"):
        AutoDriveXmlReader.load(path)


def test_mismatched_coordinate_counts_raise_value_error(write_xml):
    path = write_xml(x="1;2;3", y="1;2", z="1;2;3")

    with pytest.raises(ValueError, match="does not match"):
        AutoDriveXmlReader.load(path)


def test_invalid_coordinate_value_raises_value_error(write_xml):
    path = write_xml(x="1;abc;3")

    with pytest.raises(ValueError, match="abc"):
        AutoDriveXmlReader.load(path)


def test_invalid_connection_id_raises_value_error(write_xml):
    path = write_xml(out="2;x;")

    with pytest.raises(ValueError, match="connection ID"):
        AutoDriveXmlReader.load(path)


# --- route export details ------------------------------------------------


def test_route_export_reports_its_format(write_xml):
    loaded = AutoDriveXmlReader.read(write_xml())

    assert loaded.source.format == ConfigFormat.ROUTE_EXPORT
    assert loaded.source.map_name is None
    assert len(loaded.data) == 3


def test_empty_flag_entries_keep_later_flags_in_place(write_xml):
    path = write_xml(flags="1;;1")

    data = AutoDriveXmlReader.load(path)

    assert [data.get_node(i).flag for i in (1, 2, 3)] == [1, 0, 1]


def test_route_marker_groups_are_read_in_order_with_ids(write_xml):
    path = write_xml(
        markers='<m i="1" n="Hof" g="All"/>',
        groups='<g n="Felder" i="2"/><g n="All" i="1"/>',
    )

    data = AutoDriveXmlReader.load(path)

    assert [(g.name, g.group_id) for g in data.marker_groups] == [("Felder", 2), ("All", 1)]


def test_marker_order_follows_the_file(write_xml):
    path = write_xml(markers='<m i="3" n="C" g="All"/><m i="1" n="A" g="All"/>')

    data = AutoDriveXmlReader.load(path)

    assert list(data.markers) == [3, 1]


def test_map_scan_and_unknown_flags_are_kept_and_shown_as_regular(write_xml):
    data = AutoDriveXmlReader.load(write_xml(flags="2;4;1"))

    scanned, unknown, subprio = (data.get_node(i) for i in (1, 2, 3))
    assert (scanned.flag, unknown.flag) == (2, 4)
    assert scanned.is_regular and scanned.is_from_map_scan and scanned.has_known_flag
    assert unknown.is_regular and not unknown.has_known_flag
    assert subprio.is_subprio and subprio.has_known_flag


def test_unknown_root_element_is_rejected(write_xml):
    path = write_xml(raw="<Courseplay><waypoints/></Courseplay>")

    with pytest.raises(ValueError, match="Unknown format"):
        AutoDriveXmlReader.load(path)


# --- savegame config -----------------------------------------------------

SAVEGAME = """<?xml version="1.0" encoding="utf-8" standalone="no"?>
<AutoDrive>
    <version>{version}</version>
    <MapName>LS25_Thüringen_2_0_16x</MapName>
    <someSetting>1.000000</someSetting>
    <waypoints>
        <id>1,2,3</id>
        <x>-21.060,-24.520,-25.210</x>
        <y>100.5,101.0,102.25</y>
        <z>5.0,6.0,7.0</z>
        <out>2,3;3;-1</out>
        <incoming>-1;1;1,2</incoming>
        <flags>0,1,0</flags>
    </waypoints>
    <mapmarker>
        <mm2><id>1.000000</id><name>Hof</name><group>Höfe</group></mm2>
        <mm1><id>3.000000</id><name>Feld 1</name><group>Felder</group></mm1>
    </mapmarker>
</AutoDrive>
"""


@pytest.fixture
def write_savegame(tmp_path):
    def _write(version="3.0.1.4", text=None):
        path = tmp_path / "AutoDrive_config.xml"
        path.write_text(text or SAVEGAME.format(version=version), encoding="utf-8")
        return path

    return _write


def test_savegame_coordinates_connections_and_flags(write_savegame):
    data = AutoDriveXmlReader.load(write_savegame())

    first = data.get_node(1)
    assert (first.x, first.y, first.z) == (-21.06, 100.5, 5.0)
    assert first.outgoing == {2, 3}
    assert data.get_node(3).incoming == {1, 2}
    assert data.get_node(3).outgoing == set()
    assert [data.get_node(i).flag for i in (1, 2, 3)] == [0, 1, 0]


def test_savegame_source_has_map_name_and_version(write_savegame):
    source = AutoDriveXmlReader.read(write_savegame()).source

    assert source.format == ConfigFormat.SAVEGAME
    assert source.map_name == "LS25_Thüringen_2_0_16x"
    assert source.version == "3.0.1.4"


def test_savegame_markers_follow_mm_numbers(write_savegame):
    data = AutoDriveXmlReader.load(write_savegame())

    assert [(m.node_id, m.name, m.group) for m in data.markers.values()] == [
        (3, "Feld 1", "Felder"),
        (1, "Hof", "Höfe"),
    ]


def test_savegame_groups_are_collected_from_markers(write_savegame):
    data = AutoDriveXmlReader.load(write_savegame())

    assert [(g.name, g.group_id) for g in data.marker_groups] == [("Felder", None), ("Höfe", None)]


@pytest.mark.parametrize("version", ["2.0.1.8", "1.1.0.6"])
def test_configs_from_older_games_are_rejected(write_savegame, version):
    with pytest.raises(ValueError, match="FS25"):
        AutoDriveXmlReader.load(write_savegame(version=version))


def test_savegame_without_version_is_rejected(write_savegame):
    text = SAVEGAME.format(version="").replace("<version></version>", "")

    with pytest.raises(ValueError, match="version"):
        AutoDriveXmlReader.load(write_savegame(text=text))
