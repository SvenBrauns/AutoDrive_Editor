"""Noticing that the open file was changed by someone else."""

from game_folder_helpers import ROUTE_XML

from autodrive_editor.file_io.autodrive_xml import AutoDriveXmlReader, ConfigFormat, ConfigSource
from autodrive_editor.file_io.autodrive_xml_writer import save_config
from autodrive_editor.file_io.disk_state import file_stamp, network_fingerprint
from autodrive_editor.model.autodrive_data import AutoDriveData, MarkerData, NodeData


def network(first_id=1, x=1.23456):
    data = AutoDriveData()
    data.add_node(NodeData(first_id, x, 2.0, 3.0, outgoing={first_id + 1}))
    data.add_node(NodeData(first_id + 1, 10.0, 2.0, 3.0, incoming={first_id}))
    data.add_marker(MarkerData(first_id + 1, "Hof", "All"))
    return data


def test_a_saved_network_read_back_has_the_same_fingerprint(tmp_path):
    (tmp_path / "route.xml").write_text(ROUTE_XML, encoding="utf-8")

    for file_format, name in ((ConfigFormat.ROUTE_EXPORT, "route"), (ConfigFormat.SAVEGAME, "new")):
        path = tmp_path / f"{name}.xml"
        save_config(network(), ConfigSource(file_format, path))
        read_back = AutoDriveXmlReader.read(path).data

        assert network_fingerprint(read_back, file_format) == network_fingerprint(
            network(), file_format
        )


def test_node_ids_do_not_count():
    assert network_fingerprint(network(first_id=7), ConfigFormat.SAVEGAME) == (
        network_fingerprint(network(), ConfigFormat.SAVEGAME)
    )


def test_positions_connections_and_markers_count():
    base = network_fingerprint(network(), ConfigFormat.SAVEGAME)
    moved = network(x=1.3)
    disconnected = network()
    disconnected.nodes[1].outgoing.clear()
    renamed = network()
    renamed.markers[2].name = "Feld"

    for data in (moved, disconnected, renamed):
        assert network_fingerprint(data, ConfigFormat.SAVEGAME) != base


def test_a_missing_file_has_no_stamp(tmp_path):
    assert file_stamp(tmp_path / "missing.xml") is None
