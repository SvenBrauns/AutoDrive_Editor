from pathlib import Path

from PySide6.QtWidgets import QDialogButtonBox

from autodrive_editor.game.savegame_info import SavegameInfo
from autodrive_editor.ui.dialogs.savegame_link_dialog import SavegameLinkDialog

SAVEGAMES = [
    SavegameInfo(Path("savegame1"), 1, "Elm", "Elmcreek"),
    SavegameInfo(Path("savegame2"), 2, "Hof", "LS25 Thüringen 2.0 16x"),
    SavegameInfo(Path("savegame3"), 3, "Riverbend", "Riverbend Springs"),
]


def names(dialog):
    table = dialog.table
    return [table.topLevelItem(row).text(1) for row in range(table.topLevelItemCount())]


def test_savegames_on_the_route_map_come_first(qapp):
    dialog = SavegameLinkDialog("Route", "LS25_Thüringen_2_0_16x", SAVEGAMES, True)

    assert names(dialog) == ["Hof", "Elm", "Riverbend"]
    assert dialog.chosen_value.name == "Hof"


def test_asked_on_loading_offers_not_to_ask_again(qapp):
    dialog = SavegameLinkDialog("Route", "", SAVEGAMES, True)
    cancel = dialog.buttons.button(QDialogButtonBox.StandardButton.Cancel)

    dialog.dont_ask_check.setChecked(True)

    assert cancel.text() == "Not now"
    assert dialog.dont_ask_again


def test_from_the_menu_a_link_can_be_removed(qapp):
    dialog = SavegameLinkDialog("Route", "", SAVEGAMES, False, Path("savegame3"))
    remove = next(b for b in dialog.buttons.buttons() if b.text() == "Remove link")

    assert dialog.dont_ask_check is None
    assert dialog.chosen_value.name == "Riverbend"

    remove.click()

    assert dialog.result() == SavegameLinkDialog.REMOVE
