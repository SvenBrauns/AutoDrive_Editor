from dataclasses import dataclass, field
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from autodrive_editor.file_io.routes_index import RouteEntry
from autodrive_editor.game.savegame_info import SavegameInfo
from autodrive_editor.i18n import tr
from autodrive_editor.ui.dialogs.list_choice_dialog import ChoiceTable

SETTINGS_LINK = "settings"


@dataclass
class OpenLists:
    """What the Open screen offers. A hint replaces an empty list and may link to the
    settings."""

    savegames: list[SavegameInfo] = field(default_factory=list)
    savegames_hint: str = ""
    routes: list[RouteEntry] = field(default_factory=list)
    routes_hint: str = ""


class OpenScreen(QWidget):
    """The one way to open: the savegames (newest first), below them the routes of the
    RoutesManager, and a small link to open any other file. Shown on the map while nothing is
    open, and inside the Open dialog."""

    # The SavegameInfo or RouteEntry to open.
    chosen = Signal(object)

    browse_requested = Signal()
    settings_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.savegame_table = ChoiceTable([tr("No."), tr("Name"), tr("Map"), tr("Saved")], [])
        self.route_table = ChoiceTable([tr("Name"), tr("Map"), tr("Revision"), tr("Date")], [])
        self.savegames_hint = self._hint_label()
        self.routes_hint = self._hint_label()

        self.open_button = QPushButton(tr("Open"), self)
        self.open_button.setDefault(True)
        self.open_button.clicked.connect(self._emit_chosen)

        browse_link = self._link_label(f'<a href="browse">{tr("Open other file…")}</a>')
        browse_link.linkActivated.connect(lambda link: self.browse_requested.emit())

        for table, other in (
            (self.savegame_table, self.route_table),
            (self.route_table, self.savegame_table),
        ):
            table.itemDoubleClicked.connect(lambda item, column: self._emit_chosen())
            table.itemSelectionChanged.connect(
                lambda table=table, other=other: self._selected_in(table, other)
            )

        bottom = QHBoxLayout()
        bottom.addWidget(browse_link)
        bottom.addStretch(1)
        bottom.addWidget(self.open_button)

        layout = QVBoxLayout(self)
        layout.addWidget(self._heading(tr("Savegames")))
        layout.addWidget(self.savegames_hint)
        layout.addWidget(self.savegame_table, 3)
        layout.addSpacing(8)
        layout.addWidget(self._heading(tr("Routes (RoutesManager)")))
        layout.addWidget(self.routes_hint)
        layout.addWidget(self.route_table, 2)
        layout.addLayout(bottom)

        self.set_lists(OpenLists())

    def set_lists(self, lists: OpenLists):
        for table in (self.savegame_table, self.route_table):
            table.blockSignals(True)

        self.savegame_table.set_rows(
            [
                (
                    [
                        f"{info.number:2d}",
                        _savegame_name(info)
                        if info.has_autodrive
                        else tr("{name} (no AutoDrive network)", name=_savegame_name(info)),
                        info.map_title,
                        info.saved_text,
                    ],
                    info,
                )
                for info in lists.savegames
            ],
            sort_column=3,
            newest_first=True,
        )
        self.route_table.set_rows(
            [([e.name, e.map_name, str(e.revision), e.date], e) for e in lists.routes],
            sort_column=3,
            newest_first=True,
        )

        for table in (self.savegame_table, self.route_table):
            table.blockSignals(False)

        self._show_list(self.savegame_table, self.savegames_hint, lists.savegames_hint)
        self._show_list(self.route_table, self.routes_hint, lists.routes_hint)

        # A savegame is the usual choice: the newest one is preselected, no route.
        if self.savegame_table.topLevelItemCount():
            self._selected_in(self.savegame_table, self.route_table)

        self._update_open_button()

    @property
    def chosen_value(self) -> Any:
        for table in (self.savegame_table, self.route_table):
            if table.selectedItems():
                return table.chosen_value

        return None

    def _selected_in(self, table: ChoiceTable, other: ChoiceTable):
        if table.selectedItems():
            other.blockSignals(True)
            other.clearSelection()
            other.blockSignals(False)

        self._update_open_button()

    def _emit_chosen(self):
        if self.chosen_value is not None:
            self.chosen.emit(self.chosen_value)

    def _update_open_button(self):
        self.open_button.setEnabled(self.chosen_value is not None)

    @staticmethod
    def _show_list(table: ChoiceTable, hint_label: QLabel, hint: str):
        """An empty list is replaced by its hint."""

        has_rows = table.topLevelItemCount() > 0
        table.setVisible(has_rows)
        hint_label.setText(hint)
        hint_label.setVisible(not has_rows)

    def _heading(self, text: str) -> QLabel:
        label = QLabel(text, self)
        font = label.font()
        font.setBold(True)
        label.setFont(font)

        return label

    def _hint_label(self) -> QLabel:
        label = self._link_label("")
        label.setWordWrap(True)
        label.linkActivated.connect(lambda link: self.settings_requested.emit())

        return label

    def _link_label(self, text: str) -> QLabel:
        label = QLabel(text, self)
        label.setTextFormat(Qt.TextFormat.RichText)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.LinksAccessibleByMouse)

        return label


def settings_link(text: str) -> str:
    """A hint text with a link to the settings at its end."""

    return f'{text} <a href="{SETTINGS_LINK}">{tr("Open settings")}</a>'


def _savegame_name(info) -> str:
    """The name in the game; the number has its own column."""

    return info.name or info.directory.name
