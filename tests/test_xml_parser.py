import pytest

from autodrive_editor.file_io.autodrive_xml import AutoDriveXmlParser


def test_loads_coordinates_with_one_based_ids(write_xml):
    path = write_xml(x="1.5;2.5", y="10;20", z="-3;-4", out="", incoming="", flags="")

    data = AutoDriveXmlParser.load(path)

    assert sorted(data.nodes) == [1, 2]
    node = data.get_node(2)
    assert (node.x, node.y, node.z) == (2.5, 20.0, -4.0)


def test_loads_connections_by_position(write_xml):
    # Node 1 -> 2, node 2 -> 1 and 3, node 3 has no outgoing connection.
    path = write_xml(out="2;1,3;", incoming="2;1;2")

    data = AutoDriveXmlParser.load(path)

    assert data.get_node(1).outgoing == {2}
    assert data.get_node(2).outgoing == {1, 3}
    assert data.get_node(3).outgoing == set()
    assert data.get_node(3).incoming == {2}


def test_ignores_non_positive_connection_ids(write_xml):
    path = write_xml(out="-1;0,1;2")

    data = AutoDriveXmlParser.load(path)

    assert data.get_node(1).outgoing == set()
    assert data.get_node(2).outgoing == {1}


def test_missing_connections_and_flags_default_to_empty(write_xml):
    path = write_xml(out=None, incoming=None, flags=None)

    data = AutoDriveXmlParser.load(path)

    for node in data.nodes.values():
        assert node.outgoing == set()
        assert node.incoming == set()
        assert node.flag == 0


def test_short_flag_list_is_padded_with_zero(write_xml):
    path = write_xml(flags="1")

    data = AutoDriveXmlParser.load(path)

    assert [data.get_node(i).flag for i in (1, 2, 3)] == [1, 0, 0]


def test_loads_markers_and_skips_invalid_ones(write_xml):
    markers = (
        '<mm1 i="1" n="Hof" g="All"/>'
        '<mm2 i="99" n="Unbekannt"/>'
        '<mm3 i="abc" n="Kaputt"/>'
        '<mm4 n="Ohne ID"/>'
    )
    path = write_xml(markers=markers)

    data = AutoDriveXmlParser.load(path)

    assert list(data.markers) == [1]
    assert data.get_marker(1).name == "Hof"
    assert data.get_marker(1).group == "All"


def test_missing_file_raises_file_not_found(tmp_path):
    with pytest.raises(FileNotFoundError):
        AutoDriveXmlParser.load(tmp_path / "missing.xml")


def test_malformed_xml_raises_value_error(write_xml):
    path = write_xml(raw="<AutoDrive><waypoints>")

    with pytest.raises(ValueError, match="ungültig"):
        AutoDriveXmlParser.load(path)


def test_missing_waypoints_raises_value_error(write_xml):
    path = write_xml(raw="<AutoDrive></AutoDrive>")

    with pytest.raises(ValueError, match="Waypoint"):
        AutoDriveXmlParser.load(path)


def test_missing_coordinate_element_raises_value_error(write_xml):
    path = write_xml(raw="<AutoDrive><waypoints><x>1</x><y>1</y></waypoints></AutoDrive>")

    with pytest.raises(ValueError, match="z-Koordinaten"):
        AutoDriveXmlParser.load(path)


def test_mismatched_coordinate_counts_raise_value_error(write_xml):
    path = write_xml(x="1;2;3", y="1;2", z="1;2;3")

    with pytest.raises(ValueError, match="stimmt nicht"):
        AutoDriveXmlParser.load(path)


def test_invalid_coordinate_value_raises_value_error(write_xml):
    path = write_xml(x="1;abc;3")

    with pytest.raises(ValueError, match="abc"):
        AutoDriveXmlParser.load(path)


def test_invalid_connection_id_raises_value_error(write_xml):
    path = write_xml(out="2;x;")

    with pytest.raises(ValueError, match="Verbindungs-ID"):
        AutoDriveXmlParser.load(path)
