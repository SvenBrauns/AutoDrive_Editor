from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QUndoCommand, QUndoGroup, QUndoStack

from autodrive_editor.editing.commands.edit_command import DataChange, EditCommand
from autodrive_editor.i18n import tr


class PlanCommand(QUndoCommand):
    """An applied plan as one undo step. It keeps the plan's own undo
    stack and moves it to its end or back to its start."""

    def __init__(self, plan_stack: QUndoStack):
        super().__init__(tr("Plan applied"))

        self.plan_stack = plan_stack

        self._applied_index = plan_stack.index()

    def redo(self):
        self.plan_stack.setIndex(self._applied_index)

    def undo(self):
        self.plan_stack.setIndex(0)


class EditHistory(QObject):
    """Runs all edits through one undo history."""

    data_changed = Signal(object)

    clean_changed = Signal(bool)

    planning_changed = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.undo_stack = QUndoStack(self)

        # Undo and redo actions follow the active stack: the plan's stack
        # while a plan is open, else the main stack.
        self.undo_group = QUndoGroup(self)
        self.undo_group.addStack(self.undo_stack)
        self.undo_group.setActiveStack(self.undo_stack)

        self._plan_stack: QUndoStack | None = None

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
        return self._active_stack.canUndo()

    @property
    def can_redo(self) -> bool:
        return self._active_stack.canRedo()

    @property
    def is_planning(self) -> bool:
        return self._plan_stack is not None

    @property
    def _active_stack(self) -> QUndoStack:
        return self._plan_stack or self.undo_stack

    def push(self, command: EditCommand):
        if not isinstance(command, EditCommand):
            raise TypeError("Invalid edit command.")

        command.set_change_listener(self._handle_data_change)

        # QUndoStack.push() runs command.redo() immediately.
        self._active_stack.push(command)

    def undo(self):
        if self._history_locked:
            return

        self._active_stack.undo()

    def redo(self):
        if self._history_locked:
            return

        self._active_stack.redo()

    def start_plan(self):
        """Following edits go into the plan, which keeps its own undo
        history until it is applied or discarded."""

        if self.is_planning:
            return

        # No parent: the plan stack lives as long as its PlanCommand.
        self._plan_stack = QUndoStack()
        self.undo_group.addStack(self._plan_stack)
        self.undo_group.setActiveStack(self._plan_stack)
        self.planning_changed.emit(True)

    def apply_plan(self):
        """Adds the plan's edits to the history as one undo step."""

        plan_stack = self._end_plan()

        if plan_stack is not None and plan_stack.index() > 0:
            self.undo_stack.push(PlanCommand(plan_stack))

    def discard_plan(self):
        """Reverts all edits of the plan."""

        plan_stack = self._end_plan()

        if plan_stack is not None:
            plan_stack.setIndex(0)

    def _end_plan(self) -> QUndoStack | None:
        plan_stack = self._plan_stack

        if plan_stack is None:
            return None

        self._plan_stack = None
        self.undo_group.removeStack(plan_stack)
        self.undo_group.setActiveStack(self.undo_stack)
        self.planning_changed.emit(False)

        return plan_stack

    def clear(self):
        """Forgets the history and an open plan without reverting it,
        e.g. when other data is loaded."""

        self._end_plan()
        self.undo_stack.clear()

    def mark_clean(self):
        self.undo_stack.setClean()

    def mark_unsaved(self):
        """Counts the data as changed although nothing is in the history,
        e.g. after restoring an autosave."""

        self.undo_stack.resetClean()

    def _handle_data_change(self, data_change: DataChange):
        self.data_changed.emit(data_change)
