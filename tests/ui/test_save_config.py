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

    assert route_window.files.save_xml()

    assert not route_window.isWindowModified()
    assert len(AutoDriveXmlReader.load(route_window.route_file)) == 2
    entry = read_routes_index(route_window.route_file.parent.parent / "routes.xml")[0]
    assert entry.revision == 4


def test_original_is_backed_up_once_per_session(route_window):
    backup = route_window.route_file.with_name("abc.xml.bak")
    delete_node(route_window, 2)
    route_window.files.save_xml()
    delete_node(route_window, 3)
    route_window.files.save_xml()

    assert backup.read_text(encoding="utf-8") == ROUTE_XML
    assert (route_window.route_file.parent.parent / "routes.xml.bak").exists()


def test_savegame_save_renumbers_vehicle_markers(window, tmp_path, monkeypatch):
    (tmp_path / "AutoDrive_config.xml").write_text(SAVEGAME, encoding="utf-8")
    vehicles = tmp_path / "vehicles.xml"
    vehicles.write_text(VEHICLES, encoding="utf-8")
    messages = []
    monkeypatch.setattr(window.files, "_inform", messages.append)
    window.project_coordinator.load_xml_file(tmp_path / "AutoDrive_config.xml")
    data = window.project_coordinator.autodrive_data

    window.edit_history.push(DeleteMarkerCommand(data, 2))
    window.files.save_xml()

    text = vehicles.read_text(encoding="utf-8-sig")
    assert 'firstMarker="1" secondMarker="2"' in text
    assert "<AutoDrive/>" in text
    assert "trailer" in messages[0]
    assert (tmp_path / "vehicles.xml.bak").read_text(encoding="utf-8") == VEHICLES

    # Saved again without changes, the numbers stay.
    window.files.save_xml()
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
    route_window.files._ask_save_changes = lambda: answer

    closed = route_window.close()

    assert closed is not loaded
    assert (len(AutoDriveXmlReader.load(route_window.route_file)) == 2) is saved


def test_cancel_keeps_the_data_before_loading_other_data(route_window):
    delete_node(route_window, 2)
    route_window.files._ask_save_changes = lambda: QMessageBox.Cancel

    route_window.files.open_route()

    assert route_window.isWindowModified()
    assert len(route_window.project_coordinator.autodrive_data) == 2


@pytest.fixture
def savegame_window(window, tmp_path, monkeypatch):
    savegame = tmp_path / "savegame1"
    savegame.mkdir()
    (savegame / "AutoDrive_config.xml").write_text(SAVEGAME, encoding="utf-8")
    (savegame / "vehicles.xml").write_text(VEHICLES, encoding="utf-8")
    window.savegame = savegame
    window.messages = []
    monkeypatch.setattr(window.files, "_inform", window.messages.append)
    window.project_coordinator.load_xml_file(savegame / "AutoDrive_config.xml")
    return window


def delete_marker(window, node_id):
    window.edit_history.push(
        DeleteMarkerCommand(window.project_coordinator.autodrive_data, node_id)
    )


def test_save_as_turns_a_route_into_a_new_route(route_window):
    route_window.files._ask_route_name = lambda default: "Hof neu"
    delete_node(route_window, 2)

    assert route_window.files.save_xml_as()

    entries = read_routes_index(route_window.route_file.parent.parent / "routes.xml")
    assert [(e.name, e.map_name, e.revision) for e in entries] == [
        ("Hof", "LS25_X", 3),
        ("Hof neu", "LS25_X", 1),
    ]
    assert len(AutoDriveXmlReader.load(entries[1].path)) == 2
    assert route_window.route_file.read_text(encoding="utf-8") == ROUTE_XML
    assert route_window.project_coordinator.config_source.path == entries[1].path
    assert route_window.windowTitle() == "AutoDrive FS25 Editor – Hof neu (Route)[*]"
    assert not route_window.isWindowModified()


def test_cancelled_route_name_saves_nothing(route_window):
    route_window.files._ask_route_name = lambda default: None
    delete_node(route_window, 2)

    assert not route_window.files.save_xml_as()
    assert route_window.isWindowModified()
    assert len(read_routes_index(route_window.route_file.parent.parent / "routes.xml")) == 1


def test_save_as_writes_a_savegame_copy_without_touching_vehicles(savegame_window, tmp_path):
    target = tmp_path / "copy.xml"
    savegame_window.files._ask_save_path = lambda path: target
    delete_marker(savegame_window, 2)

    savegame_window.files.save_xml_as()
    delete_marker(savegame_window, 3)
    savegame_window.files.save_xml()

    assert "<MapName>LS25_X</MapName>" in target.read_text(encoding="utf-8-sig")
    assert len(AutoDriveXmlReader.load(target).markers) == 1
    assert (savegame_window.savegame / "vehicles.xml").read_text(encoding="utf-8") == VEHICLES
    assert savegame_window.windowTitle() == "AutoDrive FS25 Editor – copy (Savegame)[*]"


def test_autosave_only_writes_unsaved_changes(route_window):
    store = route_window.files.autosave_store

    route_window.files.autosave()
    assert store.read() is None

    delete_node(route_window, 2)
    route_window.files.autosave()
    info = store.read()
    assert info.source_path == str(route_window.route_file)
    assert len(AutoDriveXmlReader.load(store.xml_path)) == 2
    assert route_window.route_file.read_text(encoding="utf-8") == ROUTE_XML

    route_window.files.save_xml()
    assert store.read() is None


def test_discarding_changes_drops_the_autosave(route_window):
    delete_node(route_window, 2)
    route_window.files.autosave()

    route_window.close()

    assert route_window.files.autosave_store.read() is None


def test_restored_autosave_saves_into_the_original_savegame(savegame_window):
    # Marker 2 of 3 deleted: vehicles' marker 3 becomes 2, park destination 2 goes.
    delete_marker(savegame_window, 2)
    savegame_window.files.autosave()
    savegame_window.edit_history.clear()
    savegame_window.project_coordinator.load_xml_file(
        savegame_window.savegame / "AutoDrive_config.xml"
    )
    savegame_window.files._ask_restore_autosave = lambda info: True

    savegame_window.files.offer_autosave_restore()

    source = savegame_window.project_coordinator.config_source
    assert source.path == savegame_window.savegame / "AutoDrive_config.xml"
    assert list(savegame_window.project_coordinator.autodrive_data.markers) == [1, 3]
    assert savegame_window.isWindowModified()

    savegame_window.files.save_xml()

    text = (savegame_window.savegame / "vehicles.xml").read_text(encoding="utf-8-sig")
    assert 'firstMarker="1" secondMarker="2"' in text
    assert "<AutoDrive/>" in text


def test_declined_restore_drops_the_autosave(route_window):
    delete_node(route_window, 2)
    route_window.files.autosave()
    route_window.files._ask_restore_autosave = lambda info: False

    route_window.files.offer_autosave_restore()

    assert route_window.files.autosave_store.read() is None


def test_autosave_of_a_missing_file_is_kept_and_explained(route_window, monkeypatch):
    messages = []
    monkeypatch.setattr(route_window.files, "_inform", messages.append)
    delete_node(route_window, 2)
    route_window.files.autosave()
    route_window.route_file.unlink()

    route_window.files.offer_autosave_restore()

    assert "original file is missing" in messages[0]
    assert route_window.files.autosave_store.read() is not None


def test_autosave_interval_follows_the_setting(isolated_user_data, window):
    window.settings.set_autosave_minutes(0)
    window.files.apply_autosave_interval()
    assert not window.files.autosave_timer.isActive()

    window.settings.set_autosave_minutes(3)
    window.files.apply_autosave_interval()
    assert window.files.autosave_timer.interval() == 3 * 60_000
