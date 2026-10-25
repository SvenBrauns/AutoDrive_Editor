from collections.abc import Callable
from dataclasses import dataclass, field

from PySide6.QtGui import QUndoCommand

from autodrive.models import AutoDriveData


@dataclass(frozen=True)
class DataChange:
    """Describes which parts of the AutoDrive data an edit changed."""

    # Nodes whose position changed.
    moved_node_ids: frozenset[int] = field(
        default_factory=frozenset
    )

    # Nodes that were added to or removed from the data.
    added_node_ids: frozenset[int] = field(
        default_factory=frozenset
    )

    removed_node_ids: frozenset[int] = field(
        default_factory=frozenset
    )

    # Existing nodes whose incoming or outgoing connections changed.
    connection_node_ids: frozenset[int] = field(
        default_factory=frozenset
    )


class EditCommand(QUndoCommand):
    """Base class for all undoable edits.

    Subclasses change the AutoDrive data in apply() and restore it in
    revert(). Both return a DataChange, which is passed to the change
    listener so the scene can be updated.
    """

    def __init__(
        self,
        text: str,
        autodrive_data: AutoDriveData
    ):
        super().__init__(
            text
        )

        if not isinstance(
            autodrive_data,
            AutoDriveData
        ):
            raise TypeError(
                "Die AutoDrive-Daten sind ungültig."
            )

        self.autodrive_data = autodrive_data

        self._change_listener: (
            Callable[[DataChange], None] | None
        ) = None

    def set_change_listener(
        self,
        change_listener: Callable[[DataChange], None] | None
    ):
        self._change_listener = change_listener

    def redo(self):
        self._notify(
            self.apply()
        )

    def undo(self):
        self._notify(
            self.revert()
        )

    def apply(self) -> DataChange:
        raise NotImplementedError

    def revert(self) -> DataChange:
        raise NotImplementedError

    def _notify(
        self,
        data_change: DataChange
    ):
        if self._change_listener is not None:
            self._change_listener(
                data_change
            )
