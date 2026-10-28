"""Linking a savegame to a route shows where its vehicles park."""

import json

import pytest
from game_folder_helpers import add_routes, add_savegame, make_game_folder
from PySide6.QtWidgets import QDialog

from autodrive_editor.ui.dialogs.savegame_link_dialog import SavegameLinkDialog

MAP = "LS25_Thüringen_2_0_16x"

# Savegame marker 2 is the route's marker "Hof" (group "All"), where a vehicle parks.
CONFIG = (
    "<AutoDrive><version>3.0.1.4</version><MapName>{map}</MapName>"
    "<waypoints><id>1,2</id><x>0,10</x><y>0,0</y><z>0,0</z>"
    "<out>2;-1</out><incoming>-1;1</incoming><flags>0,0</flags></waypoints>"
    "<mapmarker><mm1><id>1</id><name>Feld</name><group>All</group></mm1>"
    "<mm2><id>2</id><name>Hof</name><group>All</group></mm2></mapmarker></AutoDrive>"
)
VEHICLES = '<vehicles><vehicle><AutoDrive parkDestination="2"/></vehicle></vehicles>'


@pytest.fixture
def link_window(window, tmp_path, monkeypatch):
    folder = make_game_folder(tmp_path / "FarmingSimulator2025")
    add_routes(folder, [("Hof Nord", "route.xml", MAP, 1)])
    add_savegame(folder, 1, "Elm", "Elmcreek", "Elmcreek")
    savegame = add_savegame(folder, 2, "Mein Hof", "LS25 Thüringen 2.0 16x", MAP)
    (savegame / "AutoDrive_config.xml").write_text(CONFIG.format(map=MAP), encoding="utf-8")
    (savegame / "vehicles.xml").write_text(VEHICLES, encoding="utf-8")

    window.settings.set_game_folder(folder)
    window.project_files.projects_directory = tmp_path / "projects"
    window.project_files.projects_directory.mkdir()
    monkeypatch.setattr(window.files, "_choose", lambda title, hint, columns, rows, **_: rows[0][1])

    window.dialogs = []
    window.project_answer = None
    monkeypatch.setattr(
        window.savegame_link, "_ask_project_path", lambda source: window.project_answer
    )
    window.route_path = folder / "modSettings/FS25_AutoDrive/routesManager/routes/route.xml"
    window.savegame = savegame
    return window


def answer(window, result=QDialog.DialogCode.Accepted.value, dont_ask=False):
    """The link dialog is answered with result; the first row is chosen."""

    def run(dialog):
        window.dialogs.append(dialog)
        if dialog.dont_ask_check is not None:
            dialog.dont_ask_check.setChecked(dont_ask)
        return result

    window.savegame_link._run_dialog = run


def parking_names(window):
    return [marker.name for marker in window.scene_renderer.parking_markers]


def test_opening_a_route_asks_and_shows_the_parking_of_the_chosen_savegame(link_window):
    answer(link_window)

    link_window.files.open_route()

    assert link_window.dialogs[0].chosen_value.name == "Mein Hof"
    assert parking_names(link_window) == ["Hof"]
    assert link_window.status.text() == "“Mein Hof” linked for this session"
    assert list(link_window.project_files.projects_directory.iterdir()) == []


def test_not_now_with_dont_ask_again_is_remembered_for_the_route(link_window):
    answer(link_window, QDialog.DialogCode.Rejected.value, dont_ask=True)
    link_window.files.open_route()

    link_window.files.open_route()

    assert len(link_window.dialogs) == 1
    assert parking_names(link_window) == []
    assert not link_window.settings.asks_for_savegame(link_window.route_path)
    link_window.settings.set_asks_for_savegame(link_window.route_path, True)


def test_link_is_kept_in_a_new_project_and_used_next_time(link_window):
    link_window.project_answer = link_window.project_files.projects_directory / "hof.json"
    answer(link_window)
    link_window.files.open_route()

    link_window.files.open_route()

    assert len(link_window.dialogs) == 1
    assert parking_names(link_window) == ["Hof"]
    stored = json.loads(link_window.project_answer.read_text(encoding="utf-8"))
    assert stored["savegame"].endswith("savegame2")


def test_link_goes_into_the_existing_project_of_the_route(link_window):
    project = link_window.project_files.projects_directory / "hof.json"
    link_window.project_coordinator.load_xml_file(link_window.route_path)
    link_window.project_coordinator.save_project_file(project)
    link_window.project_coordinator.current_config_path = None
    answer(link_window)

    link_window.files.open_route()

    assert link_window.project_files.stored_savegame(project) == link_window.savegame.resolve()


def test_loading_the_project_shows_the_parking(link_window):
    project = link_window.project_files.projects_directory / "hof.json"
    link_window.project_coordinator.load_xml_file(link_window.route_path)
    link_window.project_coordinator.set_savegame(link_window.savegame)
    link_window.project_coordinator.save_project_file(project)
    link_window.project_coordinator.load_xml_file(link_window.route_path)
    assert parking_names(link_window) == []

    link_window.project_coordinator.load_project_file(project)

    assert parking_names(link_window) == ["Hof"]


def test_menu_removes_the_link(link_window):
    project = link_window.project_files.projects_directory / "hof.json"
    link_window.project_answer = project
    answer(link_window)
    link_window.files.open_route()
    answer(link_window, SavegameLinkDialog.REMOVE)

    link_window.actions.link_savegame_action.trigger()

    assert parking_names(link_window) == []
    assert link_window.project_files.stored_savegame(project) is None
    assert link_window.status.text() == "Savegame link removed"


def test_savegames_are_not_asked_for_a_link(link_window):
    answer(link_window)
    link_window.files._choose = lambda title, hint, columns, rows, **_: rows[-1][1]

    link_window.files.open_savegame()

    assert link_window.dialogs == []
    assert not link_window.actions.link_savegame_action.isEnabled()


def test_debug_info_shows_the_marker_number(link_window):
    link_window.project_coordinator.load_xml_file(link_window.route_path)

    link_window.node_selection.replace([1], 1)

    assert "Number: 1" in link_window.debug_dock.node_info_value.text()
