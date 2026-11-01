from game_folder_helpers import add_routes, add_savegame, make_game_folder

from autodrive_editor.file_io.routes_index import read_routes_index
from autodrive_editor.game.game_folder import GameFolder
from autodrive_editor.game.savegame_info import savegames
from autodrive_editor.model.autodrive_data import AutoDriveData
from autodrive_editor.ui.panels.open_screen import OpenLists, OpenScreen


def lists(tmp_path):
    folder = make_game_folder(tmp_path / "FarmingSimulator2025")
    add_savegame(folder, 1, "Mein Hof", "Map", "Map_A")
    add_savegame(folder, 2, "Leer", "Map", "", with_autodrive=False)
    add_routes(folder, [("Hof Nord", "route.xml", "Map_A", 1)])
    game_folder = GameFolder(folder)

    return OpenLists(
        savegames=savegames(game_folder), routes=read_routes_index(game_folder.routes_xml_path)
    )


def test_a_savegame_is_preselected_and_a_route_click_takes_over(qapp, tmp_path):
    screen = OpenScreen()
    screen.set_lists(lists(tmp_path))

    assert screen.chosen_value.name in ("Mein Hof", "Leer")
    assert not screen.route_table.selectedItems()

    screen.route_table.setCurrentItem(screen.route_table.topLevelItem(0))

    assert screen.chosen_value.name == "Hof Nord"
    assert not screen.savegame_table.selectedItems()
    assert screen.open_button.isEnabled()


def test_savegame_without_autodrive_says_so(qapp, tmp_path):
    screen = OpenScreen()
    screen.set_lists(lists(tmp_path))
    table = screen.savegame_table
    names = [table.topLevelItem(row).text(1) for row in range(table.topLevelItemCount())]

    assert sorted(names) == ["Leer (no AutoDrive network)", "Mein Hof"]


def test_empty_lists_show_their_hints(qapp):
    screen = OpenScreen()
    screen.set_lists(OpenLists(savegames_hint="no savegames", routes_hint="no routes"))

    assert screen.savegame_table.isHidden() and screen.route_table.isHidden()
    assert not screen.savegames_hint.isHidden()
    assert screen.routes_hint.text() == "no routes"
    assert not screen.open_button.isEnabled()


def test_open_button_and_links_emit_their_signals(qapp, tmp_path):
    screen = OpenScreen()
    screen.set_lists(lists(tmp_path))
    received = []
    screen.chosen.connect(received.append)
    screen.browse_requested.connect(lambda: received.append("browse"))
    screen.settings_requested.connect(lambda: received.append("settings"))

    screen.open_button.click()
    screen.savegames_hint.linkActivated.emit("settings")

    assert received == [screen.chosen_value, "settings"]


def test_open_screen_lies_on_the_map_until_data_is_loaded(window):
    window.show()
    assert window.open_screen.isVisible()

    window._handle_autodrive_data_loaded(AutoDriveData())

    assert not window.open_screen.isVisible()
