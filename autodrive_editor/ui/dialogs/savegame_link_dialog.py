from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QDialogButtonBox

from autodrive_editor.game.savegame_info import SavegameInfo
from autodrive_editor.i18n import tr
from autodrive_editor.ui.dialogs.list_choice_dialog import ListChoiceDialog


class SavegameLinkDialog(ListChoiceDialog):
    """Asks which savegame to link to a route. Savegames on the route's map
    come first. Asked on loading, it offers not to ask again; with a link,
    it offers to remove it (result REMOVE)."""

    REMOVE = 2

    def __init__(
        self,
        route_name: str,
        map_name: str,
        savegames: list[SavegameInfo],
        asked_on_loading: bool,
        linked_directory: Path | None = None,
        parent=None,
    ):
        same_map = [info for info in savegames if info.autodrive_map_name == map_name]
        others = [info for info in savegames if info not in same_map]

        super().__init__(
            tr("Link a savegame to “{name}”", name=route_name),
            tr(
                "The editor shows where the savegame's vehicles park. "
                "Savegames on the route's map are listed first."
            ),
            [tr("No."), tr("Name"), tr("Map"), tr("Saved")],
            [
                ([f"{info.number:2d}", info.display_name, info.map_title, info.save_date], info)
                for info in same_map + others
            ],
            ok_text=tr("Link"),
            sort_column=None,
            parent=parent,
        )

        self.dont_ask_check = None

        if asked_on_loading:
            self.buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(tr("Not now"))
            self.dont_ask_check = QCheckBox(tr("Don't ask again for this route"), self)
            self.layout().insertWidget(2, self.dont_ask_check)

        if linked_directory is not None:
            remove_button = self.buttons.addButton(
                tr("Remove link"), QDialogButtonBox.ButtonRole.DestructiveRole
            )
            remove_button.clicked.connect(lambda: self.done(self.REMOVE))
            self._select(Path(linked_directory))

    @property
    def dont_ask_again(self) -> bool:
        return self.dont_ask_check is not None and self.dont_ask_check.isChecked()

    def _select(self, directory: Path):
        for row in range(self.table.topLevelItemCount()):
            item = self.table.topLevelItem(row)

            if item.data(0, Qt.ItemDataRole.UserRole).directory.resolve() == directory.resolve():
                self.table.setCurrentItem(item)
                return
