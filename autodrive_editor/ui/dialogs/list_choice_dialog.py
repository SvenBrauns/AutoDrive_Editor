from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
)

from autodrive_editor.i18n import tr


class ListChoiceDialog(QDialog):
    """Lets the user pick one row of a table, e.g. a route or a savegame.
    Each row carries a value that `chosen_value` returns. With sort_column
    None the rows keep their order until a column header is clicked."""

    def __init__(
        self,
        title: str,
        hint: str,
        columns: list[str],
        rows: list[tuple[list[str], Any]],
        ok_text: str | None = None,
        sort_column: int | None = 0,
        newest_first: bool = False,
        parent=None,
    ):
        super().__init__(parent)

        self.setWindowTitle(title)
        self.resize(720, 360)

        hint_label = QLabel(hint, self)
        hint_label.setWordWrap(True)

        self.table = QTreeWidget(self)
        self.table.setColumnCount(len(columns))
        self.table.setHeaderLabels(columns)
        self.table.setRootIsDecorated(False)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)

        if sort_column is None:
            self.table.header().setSortIndicator(-1, Qt.SortOrder.AscendingOrder)

        self.table.setSortingEnabled(True)

        for texts, value in rows:
            item = QTreeWidgetItem(texts)
            item.setData(0, Qt.ItemDataRole.UserRole, value)
            self.table.addTopLevelItem(item)

        for column in range(len(columns)):
            self.table.resizeColumnToContents(column)

        if sort_column is not None:
            self.table.sortItems(
                sort_column,
                Qt.SortOrder.DescendingOrder if newest_first else Qt.SortOrder.AscendingOrder,
            )

        self.table.itemDoubleClicked.connect(lambda item, column: self.accept())

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self
        )
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setText(ok_text or tr("Open"))
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        self.table.itemSelectionChanged.connect(self._update_ok_button)

        if self.table.topLevelItemCount():
            self.table.setCurrentItem(self.table.topLevelItem(0))

        self._update_ok_button()

        layout = QVBoxLayout(self)
        layout.addWidget(hint_label)
        layout.addWidget(self.table, 1)
        layout.addWidget(self.buttons)

    @property
    def chosen_value(self) -> Any:
        item = self.table.currentItem()

        return None if item is None else item.data(0, Qt.ItemDataRole.UserRole)

    def _update_ok_button(self):
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
            self.table.currentItem() is not None
        )
