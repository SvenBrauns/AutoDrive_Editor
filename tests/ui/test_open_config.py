"""File → Open…: routes, savegames and XML files from the game folder."""

import pytest
from game_folder_helpers import add_routes, add_savegame, make_game_folder
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFileDialog

from autodrive_editor.file_io.autodrive_xml import ConfigFormat
from autodrive_editor.game.game_folder import GameFolder
from autodrive_editor.game.savegame_info import savegames
from autodrive_editor.ui.dialogs.list_choice_dialog import ListChoiceDialog
from autodrive_editor.ui.dialogs.open_dialog import OpenDialog
from autodrive_editor.ui.panels.open_screen import OpenLists

ROUTES = [
    ("Thueringen", "g8Cq.xml", "LS25_Thüringen_2_0_16x", 1),
    ("NF Marsch", "I0pc.xml", "NF_Marsch_4fach_oG", 7),
]


@pytest.fixture
def game_window(window, tmp_path, monkeypatch):
    folder = make_game_folder(tmp_path / "FarmingSimulator2025")
    window.settings.set_game_folder(folder)

    def choose(name):
        """The open dialog picks the route or savegame with this name."""

        def ask():
            window.offered = window.files.open_lists()
            names = {entry.name: entry for entry in window.offered.routes}
            names.update({info.name: info for info in window.offered.savegames})
            return names.get(name)

        monkeypatch.setattr(window.files, "_ask_open", ask)

    window.choose = choose
    window.folder = folder
    return window


def test_open_lists_routes_and_loads_the_chosen_one(game_window):
    add_routes(game_window.folder, ROUTES)
    game_window.choose("NF Marsch")

    game_window.files.open()

    source = game_window.project_coordinator.config_source
    assert [entry.name for entry in game_window.offered.routes] == ["Thueringen", "NF Marsch"]
    assert source.format == ConfigFormat.ROUTE_EXPORT
    assert source.map_name == "NF_Marsch_4fach_oG"
    assert source.display_name == "NF Marsch"
    assert len(game_window.project_coordinator.autodrive_data) == 3
    assert game_window.windowTitle() == "AutoDrive FS25 Editor – NF Marsch (Route)[*]"


def test_routes_with_missing_files_are_not_offered(game_window):
    manager = add_routes(game_window.folder, ROUTES)
    (manager / "routes" / "I0pc.xml").unlink()
    game_window.choose("nothing")

    game_window.files.open()

    assert [entry.name for entry in game_window.offered.routes] == ["Thueringen"]


def test_without_routes_manager_the_routes_list_explains_it(game_window):
    game_window.choose("nothing")

    game_window.files.open()

    assert game_window.offered.routes == []
    assert "RoutesManager" in game_window.offered.routes_hint


def test_cancelling_the_choice_loads_nothing(game_window):
    add_routes(game_window.folder, ROUTES)
    game_window.choose("nothing")

    game_window.files.open()

    assert game_window.project_coordinator.autodrive_data is None


def test_open_loads_the_autodrive_config_of_a_savegame(game_window):
    add_savegame(game_window.folder, 1, "Mein Spielstand", "LS25 Thüringen 2.0 16x", "LS25_X")
    game_window.choose("Mein Spielstand")

    game_window.files.open()

    source = game_window.project_coordinator.config_source
    assert source.format == ConfigFormat.SAVEGAME
    assert source.map_name == "LS25_X"
    assert source.display_name == "savegame1 – Mein Spielstand"
    title = "AutoDrive FS25 Editor – savegame1 – Mein Spielstand (Savegame)[*]"
    assert game_window.windowTitle() == title


def test_savegame_without_autodrive_opens_empty_and_save_creates_the_config(game_window):
    directory = add_savegame(game_window.folder, 4, "Neu", "LS25 Thüringen 2.0 16x", "", False)
    game_window.choose("Neu")

    game_window.files.open()

    source = game_window.project_coordinator.config_source
    assert len(game_window.project_coordinator.autodrive_data) == 0
    assert (source.format, source.map_name) == (ConfigFormat.SAVEGAME, "LS25_Thüringen_2_0_16x")
    assert game_window.settings.recent_items == []

    game_window.files.save_xml()

    assert (directory / "AutoDrive_config.xml").is_file()


def test_without_savegames_the_list_explains_it(game_window):
    game_window.choose("nothing")

    game_window.files.open()

    assert game_window.offered.savegames == []
    assert "No savegames found" in game_window.offered.savegames_hint


def test_without_valid_game_folder_both_lists_link_to_the_settings(game_window, tmp_path):
    game_window.settings.set_game_folder(tmp_path / "not_a_game_folder")
    game_window.choose("nothing")

    game_window.files.open()

    assert 'href="settings"' in game_window.offered.savegames_hint
    assert 'href="settings"' in game_window.offered.routes_hint


def test_browse_opens_any_xml_file(game_window, monkeypatch):
    manager = add_routes(game_window.folder, ROUTES)
    monkeypatch.setattr(game_window.files, "_ask_open", lambda: OpenDialog.BROWSE)
    monkeypatch.setattr(
        QFileDialog, "getOpenFileName", lambda *args: (str(manager / "routes" / "g8Cq.xml"), "")
    )

    game_window.files.open()

    assert game_window.project_coordinator.config_source.display_name == "Thueringen"


def test_settings_link_in_the_dialog_refreshes_its_lists(game_window, monkeypatch):
    def run(dialog):
        add_savegame(game_window.folder, 1, "Mein Spielstand", "Map", "LS25_X")
        dialog.open_screen.settings_requested.emit()
        run.names = [dialog.open_screen.chosen_value.name]
        return QDialog.DialogCode.Rejected

    opened = []
    game_window.files.open_settings = lambda: opened.append(True)
    monkeypatch.setattr(OpenDialog, "exec", run)

    game_window.files.open()

    assert opened == [True]
    assert run.names == ["Mein Spielstand"]


def test_route_file_opened_by_hand_finds_its_map_name(game_window):
    manager = add_routes(game_window.folder, ROUTES)

    game_window.project_coordinator.load_xml_file(manager / "routes" / "g8Cq.xml")

    source = game_window.project_coordinator.config_source
    assert source.map_name == "LS25_Thüringen_2_0_16x"
    assert source.display_name == "Thueringen"


def test_broken_file_is_reported_instead_of_crashing(game_window, tmp_path, monkeypatch):
    messages = []
    monkeypatch.setattr(game_window.files, "_inform", messages.append)
    broken = tmp_path / "broken.xml"
    broken.write_text("<AutoDrive><version>2.0</version></AutoDrive>", encoding="utf-8")

    game_window.files._load_config(broken)

    assert "FS25" in messages[0]


def test_file_menu_offers_one_open_entry(window):
    texts = [action.text() for action in window.menuBar().actions()[0].menu().actions()]

    assert texts[:2] == ["Open…", "Open recent"]


# --- the dialogs -----------------------------------------------------------


def test_open_dialog_returns_the_chosen_row(qapp, tmp_path):
    folder = make_game_folder(tmp_path / "FarmingSimulator2025")
    add_savegame(folder, 1, "Mein Spielstand", "LS25 Thüringen 2.0 16x", "LS25_X")
    dialog = OpenDialog(OpenLists(savegames=savegames(GameFolder(folder))))
    dialog.open_screen.open_button.click()

    assert dialog.result() == QDialog.DialogCode.Accepted
    assert dialog.chosen_value.name == "Mein Spielstand"


def test_choice_dialog_returns_the_value_of_the_chosen_row(qapp):
    dialog = ListChoiceDialog("Titel", "Hinweis", ["Name"], [(["B"], 2), (["A"], 1)])

    assert dialog.chosen_value == 1  # sorted by first column, first row selected

    dialog.table.setCurrentItem(dialog.table.topLevelItem(1))
    assert dialog.chosen_value == 2


def test_choice_dialog_disables_ok_without_rows(qapp):
    dialog = ListChoiceDialog("Titel", "Hinweis", ["Name"], [])

    assert not dialog.buttons.button(QDialogButtonBox.StandardButton.Ok).isEnabled()
    assert dialog.chosen_value is None


def test_choice_dialog_can_show_newest_first(qapp):
    dialog = ListChoiceDialog(
        "Titel",
        "Hinweis",
        ["Name", "Date"],
        [(["alt", "2025/01/01"], "old"), (["new", "2026/10/23"], "new")],
        sort_column=1,
        newest_first=True,
    )

    assert dialog.chosen_value == "new"
