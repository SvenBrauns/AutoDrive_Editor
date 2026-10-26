from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDockWidget,
    QHBoxLayout,
    QMenu,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from autodrive_editor.i18n import tr
from autodrive_editor.model.autodrive_data import AutoDriveData


class MarkerDock(QDockWidget):
    """All marker groups with their markers. Clicking a marker shows it on
    the map, double-clicking edits it. Groups can be renamed, empty groups
    deleted."""

    marker_activated = Signal(int)
    edit_requested = Signal(int)
    rename_group_requested = Signal(str)
    delete_group_requested = Signal(str)

    NODE_ROLE = Qt.ItemDataRole.UserRole
    GROUP_ROLE = Qt.ItemDataRole.UserRole + 1

    EMPTY_TEXT = tr("No markers")

    def __init__(self, parent=None):
        super().__init__(tr("Markers"), parent)

        self.setObjectName("marker_dock")
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)

        self.tree = QTreeWidget(self)
        self.tree.setHeaderHidden(True)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.itemClicked.connect(self._handle_click)
        self.tree.itemDoubleClicked.connect(self._handle_double_click)
        self.tree.currentItemChanged.connect(lambda *_: self._update_buttons())
        self.tree.customContextMenuRequested.connect(self._show_context_menu)

        self.edit_button = QPushButton(tr("Edit"), self)
        self.edit_button.clicked.connect(self._request_edit)

        self.rename_button = QPushButton(tr("Rename"), self)
        self.rename_button.setToolTip(tr("Rename group"))
        self.rename_button.clicked.connect(self._request_rename)

        self.delete_button = QPushButton(tr("Delete"), self)
        self.delete_button.setToolTip(tr("Delete empty group"))
        self.delete_button.clicked.connect(self._request_delete)

        buttons = QHBoxLayout()
        buttons.addWidget(self.edit_button)
        buttons.addWidget(self.rename_button)
        buttons.addWidget(self.delete_button)

        content = QWidget(self)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addWidget(self.tree)
        layout.addLayout(buttons)

        self.setWidget(content)
        self.set_data(None)

    def set_data(self, autodrive_data: AutoDriveData | None):
        """Rebuilds the tree. Collapsed groups, the current item and the
        scroll position stay."""

        collapsed = {
            item.data(0, self.GROUP_ROLE) for item in self._group_items() if not item.isExpanded()
        }
        current = self._current_key()
        scroll_position = self.tree.verticalScrollBar().value()

        self.tree.clear()

        if autodrive_data is None or not (autodrive_data.markers or autodrive_data.marker_groups):
            placeholder = QTreeWidgetItem([self.EMPTY_TEXT])
            placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
            self.tree.addTopLevelItem(placeholder)
            self._update_buttons()
            return

        positions = {node_id: index for index, node_id in enumerate(autodrive_data.markers)}

        for group_name in sorted(autodrive_data.marker_group_names(), key=str.casefold):
            markers = sorted(
                autodrive_data.markers_in_group(group_name), key=lambda m: m.name.casefold()
            )

            group_item = QTreeWidgetItem([f"{group_name} ({len(markers)})"])
            group_item.setData(0, self.GROUP_ROLE, group_name)
            self.tree.addTopLevelItem(group_item)

            for marker in markers:
                marker_item = QTreeWidgetItem([marker.name])
                marker_item.setData(0, self.NODE_ROLE, marker.node_id)
                marker_item.setToolTip(
                    0,
                    tr(
                        "Marker no. {number}, node {node}",
                        number=positions[marker.node_id] + 1,
                        node=marker.node_id,
                    ),
                )
                group_item.addChild(marker_item)

            group_item.setExpanded(group_name not in collapsed)

        self._restore_current(current)
        self.tree.verticalScrollBar().setValue(scroll_position)
        self._update_buttons()

    def marker_item(self, node_id: int) -> QTreeWidgetItem | None:
        for group_item in self._group_items():
            for index in range(group_item.childCount()):
                child = group_item.child(index)

                if child.data(0, self.NODE_ROLE) == node_id:
                    return child

        return None

    def group_item(self, name: str) -> QTreeWidgetItem | None:
        return next(
            (item for item in self._group_items() if item.data(0, self.GROUP_ROLE) == name), None
        )

    def _group_items(self) -> list[QTreeWidgetItem]:
        items = (self.tree.topLevelItem(i) for i in range(self.tree.topLevelItemCount()))
        return [item for item in items if item.data(0, self.GROUP_ROLE) is not None]

    def _current_key(self):
        item = self.tree.currentItem()

        if item is None:
            return None

        return item.data(0, self.NODE_ROLE), item.data(0, self.GROUP_ROLE)

    def _restore_current(self, key):
        if key is None:
            return

        node_id, group_name = key
        item = self.marker_item(node_id) if node_id is not None else self.group_item(group_name)

        if item is not None:
            self.tree.setCurrentItem(item)

    def _selected(self):
        """(node id, group name, marker count) of the current item."""

        item = self.tree.currentItem()

        if item is None:
            return None, None, 0

        return item.data(0, self.NODE_ROLE), item.data(0, self.GROUP_ROLE), item.childCount()

    def _update_buttons(self):
        node_id, group_name, count = self._selected()

        self.edit_button.setEnabled(node_id is not None)
        self.rename_button.setEnabled(group_name is not None)
        self.delete_button.setEnabled(group_name is not None and count == 0)

    def _handle_click(self, item: QTreeWidgetItem, column: int):
        node_id = item.data(0, self.NODE_ROLE)

        if node_id is not None:
            self.marker_activated.emit(node_id)

    def _handle_double_click(self, item: QTreeWidgetItem, column: int):
        node_id = item.data(0, self.NODE_ROLE)

        if node_id is not None:
            self.edit_requested.emit(node_id)

    def _request_edit(self):
        node_id, _, _ = self._selected()

        if node_id is not None:
            self.edit_requested.emit(node_id)

    def _request_rename(self):
        _, group_name, _ = self._selected()

        if group_name is not None:
            self.rename_group_requested.emit(group_name)

    def _request_delete(self):
        _, group_name, count = self._selected()

        if group_name is not None and count == 0:
            self.delete_group_requested.emit(group_name)

    def _show_context_menu(self, position):
        item = self.tree.itemAt(position)

        if item is None:
            return

        self.tree.setCurrentItem(item)

        menu = QMenu(self)

        for button in (self.edit_button, self.rename_button, self.delete_button):
            if button.isEnabled():
                menu.addAction(button.toolTip() or button.text(), button.click)

        if not menu.isEmpty():
            menu.exec(self.tree.viewport().mapToGlobal(position))
