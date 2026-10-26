"""Saving the loaded AutoDrive data back into its file."""

import pytest
from game_folder_helpers import ROUTE_XML, add_routes
from PySide6.QtWidgets import QMessageBox

from autodrive_editor.editing.commands.delete_nodes import DeleteNodesCommand
from autodrive_editor.editing.commands.markers import DeleteMarkerCommand
from autodrive_editor.file_io.autodrive_xml import AutoDriveXmlReader
from autodrive_editor.file_io.routes_index import read_routes_index

SAVEGAME = (
    "<AutoDrive><version>3.0.1.4</version><MapName>LS25_X</MapName>"
    "<waypoints><id>1,2,3</id><x>0,10,20</x><y>0,0,0</y><z>0,0,0</z>"
    "<out>2;3;-1</out><incoming>-1;1;2</incoming><flags>0,0,0</flags></waypoints>"
    "<mapmarker><mm1><id>1</id><name>A</name><group>All</group></mm1>"
    "<mm2><id>2</id><name>B</name><group>All</group></mm2>"
    "<mm3><id>3</id><name>C</name><group>All</group></mm3></mapmarker></AutoDrive>"
)

VEHICLES = (
    '<vehicles><vehicle filename="data/vehicles/a/tractor.xml">'
    '<AutoDrive firstMarker="1" secondMarker="3" driverName="Zug"/></vehicle>'
    '<vehicle filename="data/vehicles/b/trailer.xml"><AutoDrive parkDestination="2"/></vehicle>'
    "</vehicles>"
)


@pytest.fixture
def route_window(window, tmp_path):
    manager = add_routes(tmp_path, [("Hof", "abc.xml", "LS25_X", 3)])
    window.route_file = manager / "routes" / "abc.xml"
    window.project_coordinator.load_xml_file(window.route_file)
    return window


def delete_node(window, node_id):
    window.edit_history.push(
        DeleteNodesCommand(window.project_coordinator.autodrive_data, {node_id})
    )


def test_save_is_only_possible_with_loaded_data(window):
    assert not window.actions.save_xml_action.isEnabled()


def test_save_writes_the_route_and_clears_the_modified_mark(route_window):
    delete_node(route_window, 2)
    assert route_window.isWindowModified()

    assert route_window.save_xml()

    assert not route_window.isWindowModified()
    assert len(AutoDriveXmlReader.load(route_window.route_file)) == 2
    entry = read_routes_index(route_window.route_file.parent.parent / "routes.xml")[0]
    assert entry.revision == 4


def test_original_is_backed_up_once_per_session(route_window):
    backup = route_window.route_file.with_name("abc.xml.bak")
    delete_node(route_window, 2)
    route_window.save_xml()
    delete_node(route_window, 3)
    route_window.save_xml()

    assert backup.read_text(encoding="utf-8") == ROUTE_XML
    assert (route_window.route_file.parent.parent / "routes.xml.bak").exists()


def test_savegame_save_renumbers_vehicle_markers(window, tmp_path, monkeypatch):
    (tmp_path / "AutoDrive_config.xml").write_text(SAVEGAME, encoding="utf-8")
    vehicles = tmp_path / "vehicles.xml"
    vehicles.write_text(VEHICLES, encoding="utf-8")
    messages = []
    monkeypatch.setattr(window, "_inform", messages.append)
    window.project_coordinator.load_xml_file(tmp_path / "AutoDrive_config.xml")
    data = window.project_coordinator.autodrive_data

    window.edit_history.push(DeleteMarkerCommand(data, 2))
    window.save_xml()

    text = vehicles.read_text(encoding="utf-8-sig")
    assert 'firstMarker="1" secondMarker="2"' in text
    assert "<AutoDrive/>" in text
    assert "trailer" in messages[0]
    assert (tmp_path / "vehicles.xml.bak").read_text(encoding="utf-8") == VEHICLES

    # Saved again without changes, the numbers stay.
    window.save_xml()
    assert 'secondMarker="2"' in vehicles.read_text(encoding="utf-8-sig")


@pytest.mark.parametrize(
    ("answer", "saved", "loaded"),
    [
        (QMessageBox.Save, True, False),
        (QMessageBox.Discard, False, False),
        (QMessageBox.Cancel, False, True),
    ],
)
def test_closing_with_unsaved_changes_asks_first(route_window, answer, saved, loaded):
    delete_node(route_window, 2)
    route_window._ask_save_changes = lambda: answer

    closed = route_window.close()

    assert closed is not loaded
    assert (len(AutoDriveXmlReader.load(route_window.route_file)) == 2) is saved


def test_cancel_keeps_the_data_before_loading_other_data(route_window):
    delete_node(route_window, 2)
    route_window._ask_save_changes = lambda: QMessageBox.Cancel

    route_window.open_route()

    assert route_window.isWindowModified()
    assert len(route_window.project_coordinator.autodrive_data) == 2
