"""Warning before Save when the game changed the open file, and File → Reload."""

import os

import pytest
from game_folder_helpers import ROUTE_XML, add_routes
from PySide6.QtWidgets import QMessageBox

from autodrive_editor.editing.commands.delete_nodes import DeleteNodesCommand
from autodrive_editor.file_io.autodrive_xml import AutoDriveXmlReader


@pytest.fixture
def route_window(window, tmp_path):
    manager = add_routes(tmp_path, [("Hof", "abc.xml", "LS25_X", 3)])
    window.route_file = manager / "routes" / "abc.xml"
    window.project_coordinator.load_xml_file(window.route_file)
    window.asked = []
    return window


def answer_changed_file(window, answer):
    def ask():
        window.asked.append("changed")
        return answer

    window.files._ask_overwrite_changed_file = ask


def delete_node(window, node_id):
    window.edit_history.push(
        DeleteNodesCommand(window.project_coordinator.autodrive_data, {node_id})
    )


def write_by_game(path, text):
    """Writes the file with a time stamp the editor has not seen."""

    stamp = path.stat().st_mtime_ns
    path.write_text(text, encoding="utf-8")
    os.utime(path, ns=(stamp + 10**9, stamp + 10**9))


def test_save_without_a_change_on_disk_does_not_ask(route_window):
    answer_changed_file(route_window, QMessageBox.Cancel)
    delete_node(route_window, 2)

    assert route_window.files.save_xml()
    delete_node(route_window, 3)
    assert route_window.files.save_xml()
    assert route_window.asked == []


def test_the_same_network_written_again_is_no_change(route_window):
    answer_changed_file(route_window, QMessageBox.Cancel)
    write_by_game(route_window.route_file, ROUTE_XML.replace("><", ">\n<"))
    delete_node(route_window, 2)

    assert route_window.files.save_xml()
    assert route_window.asked == []


def test_a_changed_network_is_kept_on_cancel(route_window):
    answer_changed_file(route_window, QMessageBox.Cancel)
    changed = ROUTE_XML.replace('n="Hof"', 'n="Feld"')
    write_by_game(route_window.route_file, changed)
    delete_node(route_window, 2)

    assert not route_window.files.save_xml()
    assert route_window.asked == ["changed"]
    assert route_window.route_file.read_text(encoding="utf-8") == changed
    assert route_window.isWindowModified()


def test_save_anyway_overwrites(route_window):
    answer_changed_file(route_window, QMessageBox.Save)
    write_by_game(route_window.route_file, ROUTE_XML.replace('n="Hof"', 'n="Feld"'))
    delete_node(route_window, 2)

    assert route_window.files.save_xml()
    assert len(AutoDriveXmlReader.load(route_window.route_file)) == 2


def test_reload_instead_of_save_loads_the_file_from_disk(route_window):
    answer_changed_file(route_window, QMessageBox.Discard)
    write_by_game(route_window.route_file, ROUTE_XML.replace('n="Hof"', 'n="Feld"'))
    delete_node(route_window, 2)

    assert not route_window.files.save_xml()

    data = route_window.project_coordinator.autodrive_data
    assert len(data) == 3
    assert [marker.name for marker in data.markers.values()] == ["Feld"]
    assert not route_window.isWindowModified()


def test_reload_is_possible_once_a_file_is_open(window):
    assert not window.actions.reload_action.isEnabled()


def test_reload_asks_before_unsaved_changes_are_lost(route_window):
    route_window.files._confirm_reload = lambda name: False
    delete_node(route_window, 2)

    route_window.files.reload()
    assert len(route_window.project_coordinator.autodrive_data) == 2

    route_window.files._confirm_reload = lambda name: True
    route_window.files.reload()
    assert len(route_window.project_coordinator.autodrive_data) == 3
    assert not route_window.isWindowModified()


def test_reload_keeps_the_view(route_window):
    view = route_window.view
    view.scale(3, 3)
    transform = view.transform()

    route_window.files.reload()

    assert view.transform() == transform
