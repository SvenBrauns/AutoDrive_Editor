from collections import Counter
from pathlib import PurePosixPath

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
)

from autodrive_editor.file_io.savegame_sheds import IndoorArea
from autodrive_editor.i18n import tr


class ShedTypesDialog(QDialog):
    """Lists the building types of the loaded sheds with a check box each, grouped by their shop
    category; a category's check box ticks all its types. Unticked types are hidden on every
    map."""

    def __init__(self, areas: list[IndoorArea], hidden: set[str], parent=None):
        super().__init__(parent)

        self.setWindowTitle(tr("Sheds"))
        self.resize(560, 480)

        self._hidden = set(hidden)

        hint_label = QLabel(
            tr("Unticked building types are not shown as sheds, on any map.")
            if areas
            else tr("No sheds loaded: open a savegame or link one to the route."),
            self,
        )
        hint_label.setWordWrap(True)

        counts = Counter(area.building_file for area in areas)
        examples = {area.building_file: area for area in areas}

        self.table = QTreeWidget(self)
        self.table.setHeaderLabels([tr("Building"), tr("File"), tr("Sheds")])

        categories: dict[str, QTreeWidgetItem] = {}

        for building_file, count in counts.items():
            area = examples[building_file]
            label = area.category_label

            if label not in categories:
                categories[label] = QTreeWidgetItem([label])
                categories[label].setFlags(
                    categories[label].flags() | Qt.ItemFlag.ItemIsAutoTristate
                )
                categories[label].setData(2, Qt.ItemDataRole.DisplayRole, 0)
                self.table.addTopLevelItem(categories[label])

            category = categories[label]
            # Numbers, so the column sorts by count.
            total = category.data(2, Qt.ItemDataRole.DisplayRole) + count
            category.setData(2, Qt.ItemDataRole.DisplayRole, total)

            item = QTreeWidgetItem([area.name, PurePosixPath(building_file).name])
            item.setData(0, Qt.ItemDataRole.UserRole, building_file)
            item.setData(2, Qt.ItemDataRole.DisplayRole, count)
            category.addChild(item)
            item.setCheckState(
                0, Qt.CheckState.Unchecked if building_file in hidden else Qt.CheckState.Checked
            )

        self.table.setSortingEnabled(True)
        self.table.sortItems(0, Qt.SortOrder.AscendingOrder)
        self.table.expandAll()

        for column in range(3):
            self.table.resizeColumnToContents(column)

        show_all_button = QPushButton(tr("Show all"), self)
        show_all_button.clicked.connect(lambda: self._check_all(Qt.CheckState.Checked))
        hide_all_button = QPushButton(tr("Hide all"), self)
        hide_all_button.clicked.connect(lambda: self._check_all(Qt.CheckState.Unchecked))

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        all_buttons = QHBoxLayout()
        all_buttons.addWidget(show_all_button)
        all_buttons.addWidget(hide_all_button)
        all_buttons.addStretch(1)

        layout = QVBoxLayout(self)
        layout.addWidget(hint_label)
        layout.addWidget(self.table, 1)
        layout.addLayout(all_buttons)
        layout.addWidget(buttons)

    @property
    def hidden_types(self) -> set[str]:
        """The unticked types and the hidden types of other maps."""

        listed, unticked = set(), set()

        for item in self._items():
            building_file = item.data(0, Qt.ItemDataRole.UserRole)
            listed.add(building_file)

            if item.checkState(0) == Qt.CheckState.Unchecked:
                unticked.add(building_file)

        return (self._hidden - listed) | unticked

    def _check_all(self, state: Qt.CheckState):
        for item in self._items():
            item.setCheckState(0, state)

    def _items(self) -> list[QTreeWidgetItem]:
        """The building types, without their categories."""

        categories = [self.table.topLevelItem(i) for i in range(self.table.topLevelItemCount())]

        return [category.child(i) for category in categories for i in range(category.childCount())]
