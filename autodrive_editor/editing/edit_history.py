from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QUndoStack

from autodrive_editor.editing.commands.edit_command import DataChange, EditCommand


class EditHistory(QObject):
    """Runs all edits through one undo history."""

    data_changed = Signal(object)

    clean_changed = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.undo_stack = QUndoStack(self)

        self._history_locked = False

        self.undo_stack.cleanChanged.connect(self.clean_changed.emit)

        # QUndoStack emits signals from its destructor. Silence it once
        # teardown starts, so they don't reach already deleted receivers.
        undo_stack = self.undo_stack

        self.destroyed.connect(lambda: undo_stack.blockSignals(True))

    @property
    def history_locked(self) -> bool:
        return self._history_locked

    def set_history_locked(self, locked: bool):
        """Blocks undo and redo, e.g. while a drag is in progress."""

        self._history_locked = bool(locked)

    @property
    def is_clean(self) -> bool:
        return self.undo_stack.isClean()

    @property
    def can_undo(self) -> bool:
        return self.undo_stack.canUndo()

    @property
    def can_redo(self) -> bool:
        return self.undo_stack.canRedo()

    def push(self, command: EditCommand):
        if not isinstance(command, EditCommand):
            raise TypeError("Der Bearbeitungsbefehl ist ungültig.")

        command.set_change_listener(self._handle_data_change)

        # QUndoStack.push() runs command.redo() immediately.
        self.undo_stack.push(command)

    def undo(self):
        if self._history_locked:
            return

        self.undo_stack.undo()

    def redo(self):
        if self._history_locked:
            return

        self.undo_stack.redo()

    def clear(self):
        self.undo_stack.clear()

    def mark_clean(self):
        self.undo_stack.setClean()

    def _handle_data_change(self, data_change: DataChange):
        self.data_changed.emit(data_change)
