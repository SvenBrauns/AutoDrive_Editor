from pathlib import PurePosixPath

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
)

from autodrive_editor.file_io.savegame_buildings import BuildingGroup, BuildingType
from autodrive_editor.i18n import tr

BUILDING, CATEGORY, FILE, COUNT, GROUP = range(5)


class BuildingTypesDialog(QDialog):
    """Lists the building types of the savegame by group, each with a check box and a group
    choice; a group's check box ticks all its types. Choosing another group moves the type there.
    Unticked types are hidden; both choices apply on every map."""

    def __init__(
        self,
        types: list[BuildingType],
        groups: dict[str, BuildingGroup],
        hidden: set[str],
        parent=None,
    ):
        super().__init__(parent)

        self.setWindowTitle(tr("Building types"))
        self.resize(760, 520)

        self._types = {item.building_file: item for item in types}
        self._groups = dict(groups)
        self._hidden = set(hidden)

        hint_label = QLabel(
            tr(
                "Stations are where vehicles unload or load, sheds are halls to park in. Choose "
                "another group if a building type is in the wrong one. Unticked types are not "
                "shown. Both apply on every map."
            )
            if types
            else tr("No buildings loaded: open a savegame."),
            self,
        )
        hint_label.setWordWrap(True)

        self.table = QTreeWidget(self)
        self.table.setHeaderLabels(
            [tr("Building"), tr("Category"), tr("File"), tr("Count"), tr("Group")]
        )

        self._group_items: dict[BuildingGroup, QTreeWidgetItem] = {}

        for group in BuildingGroup:
            item = QTreeWidgetItem([group.label])
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsAutoTristate)
            self._group_items[group] = item
            self.table.addTopLevelItem(item)

        for building_type in sorted(types, key=lambda item: item.name.lower()):
            building_file = building_type.building_file
            item = QTreeWidgetItem(
                [
                    building_type.name,
                    building_type.category_label,
                    PurePosixPath(building_file).name,
                ]
            )
            item.setData(BUILDING, Qt.ItemDataRole.UserRole, building_file)
            item.setData(COUNT, Qt.ItemDataRole.DisplayRole, building_type.count)
            self._group_items[self._group(building_file)].addChild(item)
            item.setCheckState(
                BUILDING,
                Qt.CheckState.Unchecked if building_file in hidden else Qt.CheckState.Checked,
            )
            self._add_group_choice(item)

        for item in self._group_items.values():
            item.setHidden(item.childCount() == 0)

        self.table.expandAll()

        for column in range(GROUP + 1):
            self.table.resizeColumnToContents(column)

        show_all_button = QPushButton(tr("Show all"), self)
        show_all_button.clicked.connect(lambda: self._check_all(Qt.CheckState.Checked))
        hide_all_button = QPushButton(tr("Hide all"), self)
        hide_all_button.clicked.connect(lambda: self._check_all(Qt.CheckState.Unchecked))
        reset_button = QPushButton(tr("Reset"), self)
        reset_button.setToolTip(tr("Put every listed type back in its own group and show it"))
        reset_button.clicked.connect(self.reset)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        all_buttons = QHBoxLayout()
        all_buttons.addWidget(show_all_button)
        all_buttons.addWidget(hide_all_button)
        all_buttons.addWidget(reset_button)
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
            building_file = item.data(BUILDING, Qt.ItemDataRole.UserRole)
            listed.add(building_file)

            if item.checkState(BUILDING) == Qt.CheckState.Unchecked:
                unticked.add(building_file)

        return (self._hidden - listed) | unticked

    @property
    def groups(self) -> dict[str, BuildingGroup]:
        """The types moved to another group than their own, and those of other maps."""

        return {
            building_file: group
            for building_file, group in self._groups.items()
            if building_file not in self._types or group != self._types[building_file].group
        }

    def set_group(self, item: QTreeWidgetItem, group: BuildingGroup):
        """Moves a type to another group."""

        building_file = item.data(BUILDING, Qt.ItemDataRole.UserRole)
        self._groups[building_file] = group

        old_parent = item.parent()
        state = item.checkState(BUILDING)
        old_parent.removeChild(item)
        new_parent = self._group_items[group]
        new_parent.addChild(item)
        item.setCheckState(BUILDING, state)
        self._add_group_choice(item)

        old_parent.setHidden(old_parent.childCount() == 0)
        new_parent.setHidden(False)
        new_parent.setExpanded(True)

    def _group(self, building_file: str) -> BuildingGroup:
        return self._groups.get(building_file, self._types[building_file].group)

    def _add_group_choice(self, item: QTreeWidgetItem):
        choice = QComboBox(self.table)

        for group in BuildingGroup:
            choice.addItem(group.label, group)

        choice.setCurrentIndex(
            choice.findData(self._group(item.data(BUILDING, Qt.ItemDataRole.UserRole)))
        )
        choice.currentIndexChanged.connect(lambda: self.set_group(item, choice.currentData()))
        self.table.setItemWidget(item, GROUP, choice)

    def reset(self):
        """Puts every listed type back in its own group and ticks it."""

        for item in self._items():
            own_group = self._types[item.data(BUILDING, Qt.ItemDataRole.UserRole)].group

            if item.parent() is not self._group_items[own_group]:
                self.set_group(item, own_group)

        self._check_all(Qt.CheckState.Checked)

    def _check_all(self, state: Qt.CheckState):
        for item in self._items():
            item.setCheckState(BUILDING, state)

    def _items(self) -> list[QTreeWidgetItem]:
        """The building types, without their groups."""

        return [
            group.child(i)
            for group in self._group_items.values()
            for i in range(group.childCount())
        ]
