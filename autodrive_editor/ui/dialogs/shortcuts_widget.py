from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import (
    QHBoxLayout,
    QKeySequenceEdit,
    QMessageBox,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from autodrive_editor.i18n import tr
from autodrive_editor.ui.actions.shortcuts import ShortcutRegistry, find_conflict
from autodrive_editor.ui.dialogs.messages import APP_TITLE


class ShortcutsWidget(QWidget):
    """Settings tab with one key field per action, grouped like the menus. A key that is
    already used moves to the new action after asking."""

    def __init__(self, registry: ShortcutRegistry, parent=None):
        super().__init__(parent)

        self.registry = registry
        self.keys = registry.current_keys()
        self.edits: dict[str, QKeySequenceEdit] = {}

        self.tree = QTreeWidget(self)
        self.tree.setHeaderLabels([tr("Action"), tr("Shortcut")])
        self.tree.setColumnWidth(0, 300)
        groups: dict[str, QTreeWidgetItem] = {}

        for name, entry in registry.entries.items():
            if entry.group not in groups:
                groups[entry.group] = QTreeWidgetItem(self.tree, [entry.group])

            item = QTreeWidgetItem(groups[entry.group], [entry.text])
            edit = QKeySequenceEdit(self.tree)
            edit.setMaximumSequenceLength(1)
            edit.setClearButtonEnabled(True)
            edit.keySequenceChanged.connect(
                lambda sequence, name=name: self._change(name, sequence)
            )
            self.tree.setItemWidget(item, 1, edit)
            self.edits[name] = edit

        self.tree.expandAll()
        self._show_keys()

        reset_button = QPushButton(tr("Reset all"), self)
        reset_button.clicked.connect(self.reset_all)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(reset_button)

        layout = QVBoxLayout(self)
        layout.addWidget(self.tree)
        layout.addLayout(buttons)

    def changed_keys(self) -> dict[str, list[str]]:
        return self.registry.changed_keys(self.keys)

    def reset_all(self):
        self.keys = {
            name: list(entry.default_keys) for name, entry in self.registry.entries.items()
        }
        self._show_keys()

    def _change(self, name: str, sequence: QKeySequence):
        key = sequence.toString()
        other = find_conflict(self.keys, name, key) if key else None

        if other is not None:
            if not self._ask_move(key, self.registry.entries[other].text):
                self._show_keys()
                return

            self.keys[other] = [value for value in self.keys[other] if value != key]

        self.keys[name] = [key] if key else []
        self._show_keys()

    def _ask_move(self, key: str, other_text: str) -> bool:
        shortcut = QKeySequence(key).toString(QKeySequence.NativeText)
        answer = QMessageBox.question(
            self,
            APP_TITLE,
            tr(
                "{shortcut} is used by “{action}”. Assign it here instead?",
                shortcut=shortcut,
                action=other_text,
            ),
        )

        return answer == QMessageBox.StandardButton.Yes

    def _show_keys(self):
        """Shows the first key of each action; further default keys (Redo: Ctrl+Shift+Z) are
        kept but not shown."""

        for name, edit in self.edits.items():
            keys = self.keys[name]
            edit.blockSignals(True)
            edit.setKeySequence(QKeySequence(keys[0]) if keys else QKeySequence())
            edit.blockSignals(False)
