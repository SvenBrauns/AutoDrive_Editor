"""Opening routes, savegames and XML files from the game folder."""

import pytest
from game_folder_helpers import add_routes, add_savegame, make_game_folder
from PySide6.QtWidgets import QDialogButtonBox

from autodrive_editor.file_io.autodrive_xml import ConfigFormat
from autodrive_editor.ui.dialogs.list_choice_dialog import ListChoiceDialog

ROUTES = [
    ("Thueringen", "g8Cq.xml", "LS25_Thüringen_2_0_16x", 1),
    ("NF Marsch", "I0pc.xml", "NF_Marsch_4fach_oG", 7),
]


@pytest.fixture
def game_window(window, tmp_path, monkeypatch):
    folder = make_game_folder(tmp_path / "FarmingSimulator2025")
    window.settings.set_game_folder(folder)

    window.messages = []
    monkeypatch.setattr(window, "_inform", window.messages.append)

    def choose_by_name(name):
        def choose(title, hint, columns, rows, **sorting):
            window.offered = [texts for texts, _ in rows]
            return next((value for texts, value in rows if name in texts), None)

        monkeypatch.setattr(window, "_choose", choose)

    window.choose_by_name = choose_by_name
    window.folder = folder
    return window


def test_open_route_lists_routes_and_loads_the_chosen_one(game_window):
    add_routes(game_window.folder, ROUTES)
    game_window.choose_by_name("NF Marsch")

    game_window.open_route()

    source = game_window.project_coordinator.config_source
    assert [row[0] for row in game_window.offered] == ["Thueringen", "NF Marsch"]
    assert source.format == ConfigFormat.ROUTE_EXPORT
    assert source.map_name == "NF_Marsch_4fach_oG"
    assert source.display_name == "NF Marsch"
    assert len(game_window.project_coordinator.autodrive_data) == 3
    assert game_window.windowTitle() == "AutoDrive FS25 Editor – NF Marsch (Route)[*]"


def test_routes_with_missing_files_are_not_offered(game_window):
    manager = add_routes(game_window.folder, ROUTES)
    (manager / "routes" / "I0pc.xml").unlink()
    game_window.choose_by_name("nothing")

    game_window.open_route()

    assert [row[0] for row in game_window.offered] == ["Thueringen"]


def test_open_route_without_routes_manager_explains_it(game_window):
    game_window.open_route()

    assert "route list" in game_window.messages[0]


def test_cancelling_the_choice_loads_nothing(game_window):
    add_routes(game_window.folder, ROUTES)
    game_window.choose_by_name("nothing")

    game_window.open_route()

    assert game_window.project_coordinator.autodrive_data is None


def test_open_savegame_loads_its_autodrive_config(game_window):
    add_savegame(game_window.folder, 1, "Mein Spielstand", "LS25 Thüringen 2.0 16x", "LS25_X")
    game_window.choose_by_name("Mein Spielstand")

    game_window.open_savegame()

    source = game_window.project_coordinator.config_source
    assert source.format == ConfigFormat.SAVEGAME
    assert source.map_name == "LS25_X"
    assert source.display_name == "Mein Spielstand"
    assert game_window.windowTitle() == "AutoDrive FS25 Editor – Mein Spielstand (Savegame)[*]"


def test_open_savegame_without_autodrive_data_explains_it(game_window):
    game_window.open_savegame()

    assert "AutoDrive data" in game_window.messages[0]


def test_without_valid_game_folder_the_user_is_sent_to_settings(window, monkeypatch, tmp_path):
    messages = []
    monkeypatch.setattr(window, "_inform", messages.append)
    window.settings.set_game_folder(tmp_path / "not_a_game_folder")

    window.open_route()
    window.open_savegame()

    assert len(messages) == 2
    assert all("Settings" in message for message in messages)


def test_route_file_opened_by_hand_finds_its_map_name(game_window):
    manager = add_routes(game_window.folder, ROUTES)

    game_window.project_coordinator.load_xml_file(manager / "routes" / "g8Cq.xml")

    source = game_window.project_coordinator.config_source
    assert source.map_name == "LS25_Thüringen_2_0_16x"
    assert source.display_name == "Thueringen"


def test_broken_file_is_reported_instead_of_crashing(game_window, tmp_path):
    broken = tmp_path / "broken.xml"
    broken.write_text("<AutoDrive><version>2.0</version></AutoDrive>", encoding="utf-8")

    game_window._load_config(broken)

    assert "FS25" in game_window.messages[0]


def test_file_menu_offers_route_savegame_and_file(window):
    texts = [action.text() for action in window.menuBar().actions()[0].menu().actions()]

    assert texts[:3] == ["Open route…", "Open savegame…", "Open XML file…"]


# --- the choice dialog ---------------------------------------------------


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
