from typing import Any

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from autodrive_editor.file_io.routes_index import RouteEntry
from autodrive_editor.game.savegame_info import SavegameInfo
from autodrive_editor.i18n import tr
from autodrive_editor.ui.dialogs.list_choice_dialog import ChoiceTable


class OpenDialog(QDialog):
    """File → Open…: a route from the RoutesManager or a savegame, each on
    its own tab. "Browse file…" ends the dialog with BROWSE to pick any
    XML file instead. A hint explains an empty list."""

    ROUTES_TAB = 0
    SAVEGAMES_TAB = 1
    BROWSE = 2

    def __init__(
        self,
        routes: list[RouteEntry],
        routes_hint: str,
        savegames: list[SavegameInfo],
        savegames_hint: str,
        tab: int = ROUTES_TAB,
        parent=None,
    ):
        super().__init__(parent)

        self.setWindowTitle(tr("Open"))
        self.resize(720, 400)

        self.route_table = ChoiceTable(
            [tr("Name"), tr("Map"), tr("Revision"), tr("Date")],
            [([e.name, e.map_name, str(e.revision), e.date], e) for e in routes],
            sort_column=3,
            newest_first=True,
        )
        self.savegame_table = ChoiceTable(
            [tr("No."), tr("Name"), tr("Map"), tr("Saved")],
            [
                ([f"{info.number:2d}", info.display_name, info.map_title, info.save_date], info)
                for info in savegames
            ],
        )

        self.tabs = QTabWidget(self)
        self.tabs.addTab(self._page(routes_hint, self.route_table), tr("Routes"))
        self.tabs.addTab(self._page(savegames_hint, self.savegame_table), tr("Savegames"))
        self.tabs.setCurrentIndex(tab)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self
        )
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setText(tr("Open"))
        browse_button = self.buttons.addButton(
            tr("Browse file…"), QDialogButtonBox.ButtonRole.ActionRole
        )
        browse_button.clicked.connect(lambda: self.done(self.BROWSE))
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        for table in (self.route_table, self.savegame_table):
            table.itemDoubleClicked.connect(lambda item, column: self.accept())
            table.itemSelectionChanged.connect(self._update_open_button)

        self.tabs.currentChanged.connect(self._update_open_button)
        self._update_open_button()

        layout = QVBoxLayout(self)
        layout.addWidget(self.tabs, 1)
        layout.addWidget(self.buttons)

    @property
    def chosen_value(self) -> Any:
        return self._current_table().chosen_value

    def _current_table(self) -> ChoiceTable:
        return (
            self.route_table if self.tabs.currentIndex() == self.ROUTES_TAB else self.savegame_table
        )

    def _page(self, hint: str, table: ChoiceTable) -> QWidget:
        page = QWidget(self)
        hint_label = QLabel(hint, page)
        hint_label.setWordWrap(True)

        layout = QVBoxLayout(page)
        layout.addWidget(hint_label)
        layout.addWidget(table, 1)

        return page

    def _update_open_button(self):
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
            self.chosen_value is not None
        )
