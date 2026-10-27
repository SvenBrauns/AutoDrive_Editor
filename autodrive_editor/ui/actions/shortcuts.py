"""Keyboard shortcuts that can be changed in the settings."""

from dataclasses import dataclass

from PySide6.QtGui import QAction, QKeySequence


@dataclass(frozen=True)
class ShortcutEntry:
    """An action whose shortcut can be changed. Keys are in Qt's portable
    text, e.g. "Ctrl+S"; an action can have several (Redo: Ctrl+Y and
    Ctrl+Shift+Z)."""

    name: str
    group: str
    text: str
    action: QAction
    default_keys: tuple[str, ...]


class ShortcutRegistry:
    def __init__(self):
        self.entries: dict[str, ShortcutEntry] = {}

    def add(self, name: str, group: str, action: QAction, text: str | None = None):
        """Registers the action with its current shortcuts as defaults."""

        keys = tuple(sequence.toString() for sequence in action.shortcuts())
        self.entries[name] = ShortcutEntry(name, group, text or action.text(), action, keys)

    def apply(self, changed: dict[str, list[str]]):
        """Sets the changed shortcuts and the defaults for all others."""

        for name, entry in self.entries.items():
            keys = changed.get(name, entry.default_keys)
            entry.action.setShortcuts([QKeySequence(key) for key in keys])

    def current_keys(self) -> dict[str, list[str]]:
        return {
            name: [sequence.toString() for sequence in entry.action.shortcuts()]
            for name, entry in self.entries.items()
        }

    def changed_keys(self, keys: dict[str, list[str]]) -> dict[str, list[str]]:
        """The entries of keys that differ from the defaults, for storing."""

        return {
            name: value
            for name, value in keys.items()
            if name in self.entries and tuple(value) != self.entries[name].default_keys
        }


def find_conflict(keys: dict[str, list[str]], name: str, key: str) -> str | None:
    """The other action that already uses key, or None."""

    return next((other for other, values in keys.items() if other != name and key in values), None)
