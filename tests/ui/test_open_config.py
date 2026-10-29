"""File → Open…: routes, savegames and XML files from the game folder."""

import pytest
from game_folder_helpers import add_routes, add_savegame, make_game_folder
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFileDialog

from autodrive_editor.file_io.autodrive_xml import ConfigFormat
from autodrive_editor.game.game_folder import GameFolder
from autodrive_editor.game.savegame_info import savegames_with_autodrive
from autodrive_editor.ui.dialogs.list_choice_dialog import ListChoiceDialog
from autodrive_editor.ui.dialogs.open_dialog import OpenDialog

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

        def ask(routes, routes_hint, savegames, savegames_hint):
            window.offered = (routes, routes_hint, savegames, savegames_hint)
            names = {entry.name: entry for entry in routes}
            names.update({info.display_name: info for info in savegames})
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
    assert [entry.name for entry in game_window.offered[0]] == ["Thueringen", "NF Marsch"]
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

    assert [entry.name for entry in game_window.offered[0]] == ["Thueringen"]


def test_without_routes_manager_the_routes_tab_explains_it(game_window):
    game_window.choose("nothing")

    game_window.files.open()

    assert game_window.offered[0] == []
    assert "route list" in game_window.offered[1]


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
    assert source.display_name == "Mein Spielstand"
    assert game_window.windowTitle() == "AutoDrive FS25 Editor – Mein Spielstand (Savegame)[*]"


def test_without_savegames_the_savegames_tab_explains_it(game_window):
    game_window.choose("nothing")

    game_window.files.open()

    assert game_window.offered[2] == []
    assert "AutoDrive data" in game_window.offered[3]


def test_without_valid_game_folder_both_tabs_send_the_user_to_settings(game_window, tmp_path):
    game_window.settings.set_game_folder(tmp_path / "not_a_game_folder")
    game_window.choose("nothing")

    game_window.files.open()

    assert "Settings" in game_window.offered[1]
    assert "Settings" in game_window.offered[3]


def test_browse_opens_any_xml_file(game_window, monkeypatch):
    manager = add_routes(game_window.folder, ROUTES)
    monkeypatch.setattr(game_window.files, "_ask_open", lambda *args: OpenDialog.BROWSE)
    monkeypatch.setattr(
        QFileDialog, "getOpenFileName", lambda *args: (str(manager / "routes" / "g8Cq.xml"), "")
    )

    game_window.files.open()

    assert game_window.project_coordinator.config_source.display_name == "Thueringen"


def test_open_dialog_remembers_the_last_tab(game_window, monkeypatch):
    def run(dialog):
        dialog.tabs.setCurrentIndex(OpenDialog.SAVEGAMES_TAB)
        return QDialog.DialogCode.Rejected

    monkeypatch.setattr(OpenDialog, "exec", run)

    game_window.files.open()

    assert game_window.settings.open_tab == OpenDialog.SAVEGAMES_TAB


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


def test_open_dialog_returns_the_row_of_the_current_tab(qapp, tmp_path):
    folder = make_game_folder(tmp_path / "FarmingSimulator2025")
    add_savegame(folder, 1, "Mein Spielstand", "LS25 Thüringen 2.0 16x", "LS25_X")
    savegames = savegames_with_autodrive(GameFolder(folder))
    dialog = OpenDialog([], "no routes", savegames, "hint")
    open_button = dialog.buttons.button(QDialogButtonBox.StandardButton.Ok)

    assert dialog.chosen_value is None
    assert not open_button.isEnabled()

    dialog.tabs.setCurrentIndex(OpenDialog.SAVEGAMES_TAB)

    assert dialog.chosen_value == savegames[0]
    assert open_button.isEnabled()


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
