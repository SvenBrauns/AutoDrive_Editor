from collections.abc import Callable

from PySide6.QtCore import QObject, QPoint, Signal

from autodrive_editor.editing.commands.markers import (
    AddMarkerCommand,
    DeleteMarkerCommand,
    DeleteMarkerGroupCommand,
    EditMarkerCommand,
    MoveMarkerCommand,
    RenameMarkerGroupCommand,
)
from autodrive_editor.editing.edit_history import EditHistory
from autodrive_editor.i18n import tr
from autodrive_editor.model.autodrive_data import AutoDriveData, MarkerData
from autodrive_editor.selection.node_selection import NodeSelection
from autodrive_editor.selection.selection_coordinator import SelectionCoordinator

# Asks the user for a marker's name and group. Arguments: dialog title,
# the marker being edited (None for a new one), the suggested group,
# all group names, and the (name, group) pairs other markers already
# use. Returns (name, group), or None if cancelled.
MarkerRequest = Callable[
    [str, MarkerData | None, str, list[str], set[tuple[str, str]]], tuple[str, str] | None
]


class MarkerOperation(QObject):
    """Adds, edits, moves and deletes markers and renames or deletes
    marker groups, all through the undo history."""

    status_changed = Signal(str)

    DEFAULT_GROUP = "All"

    def __init__(
        self,
        selection_coordinator: SelectionCoordinator,
        node_selection: NodeSelection,
        edit_history: EditHistory,
        autodrive_data_provider: Callable[[], AutoDriveData | None],
        ask_marker: MarkerRequest,
        parent=None,
    ):
        super().__init__(parent)

        self.selection_coordinator = selection_coordinator
        self.node_selection = node_selection
        self.edit_history = edit_history
        self.autodrive_data_provider = autodrive_data_provider
        self.ask_marker = ask_marker

        # New markers suggest the group used last.
        self.last_group = self.DEFAULT_GROUP

        # Node whose marker the move tool has picked up.
        self.move_source_id: int | None = None

        # Selection before a marker was picked up; restored afterwards.
        self._selection_before_move: tuple[set[int], int | None] | None = None

    def add_at(self, view_position: QPoint) -> bool:
        target = self._node_at(view_position)

        if target is None:
            return False

        autodrive_data, node_id = target
        existing = autodrive_data.get_marker(node_id)

        if existing is not None:
            self.status_changed.emit(
                tr("Node {node} already has the marker “{name}”", node=node_id, name=existing.name)
            )
            return False

        values = self.ask_marker(
            tr("Add marker"),
            None,
            self._suggested_group(autodrive_data),
            autodrive_data.marker_group_names(),
            self._taken_names(autodrive_data),
        )

        if values is None:
            return False

        name, group = values
        self.edit_history.push(AddMarkerCommand(autodrive_data, node_id, name, group))
        self.last_group = group
        self.status_changed.emit(tr("Marker “{name}” added", name=name))

        return True

    def edit_at(self, view_position: QPoint) -> bool:
        target = self._node_at(view_position)

        if target is None:
            return False

        autodrive_data, node_id = target

        if autodrive_data.get_marker(node_id) is None:
            self.status_changed.emit(tr("Node {node} has no marker", node=node_id))
            return False

        return self.edit_marker(node_id)

    def edit_marker(self, node_id: int) -> bool:
        autodrive_data = self.autodrive_data_provider()

        if autodrive_data is None or self.edit_history.history_locked:
            return False

        marker = autodrive_data.get_marker(node_id)

        if marker is None:
            return False

        values = self.ask_marker(
            tr("Edit marker"),
            marker,
            marker.group,
            autodrive_data.marker_group_names(),
            self._taken_names(autodrive_data, except_node_id=node_id),
        )

        if values is None or values == (marker.name, marker.group):
            return False

        name, group = values
        self.edit_history.push(EditMarkerCommand(autodrive_data, node_id, name, group))
        self.last_group = group
        self.status_changed.emit(tr("Marker “{name}” changed", name=name))

        return True

    def delete_at(self, view_position: QPoint) -> bool:
        target = self._node_at(view_position)

        if target is None:
            return False

        autodrive_data, node_id = target
        marker = autodrive_data.get_marker(node_id)

        if marker is None:
            self.status_changed.emit(tr("Node {node} has no marker", node=node_id))
            return False

        self.edit_history.push(DeleteMarkerCommand(autodrive_data, node_id))
        self.status_changed.emit(tr("Marker “{name}” deleted", name=marker.name))

        return True

    def move_click(self, view_position: QPoint) -> bool:
        """First click picks up a marker, the second puts it on another
        node. Returns True if the click did something."""

        target = self._node_at(view_position)

        if target is None:
            return False

        autodrive_data, node_id = target

        if self.move_source_id is None or self.move_source_id not in autodrive_data.markers:
            return self._pick_up_marker(autodrive_data, node_id)

        if node_id == self.move_source_id:
            return self.cancel_move()

        existing = autodrive_data.get_marker(node_id)

        if existing is not None:
            self.status_changed.emit(
                tr("Node {node} already has the marker “{name}”", node=node_id, name=existing.name)
            )
            return False

        marker = autodrive_data.get_marker(self.move_source_id)
        self.edit_history.push(MoveMarkerCommand(autodrive_data, self.move_source_id, node_id))
        self.move_source_id = None
        self._restore_selection()
        self.status_changed.emit(
            tr("Marker “{name}” moved to node {node}", name=marker.name, node=node_id)
        )

        return True

    def cancel_move(self) -> bool:
        if self.move_source_id is None:
            return False

        self.move_source_id = None
        self._restore_selection()
        self.status_changed.emit(tr("Moving the marker cancelled"))

        return True

    def rename_group(self, old_name: str, new_name: str) -> bool:
        autodrive_data = self.autodrive_data_provider()
        new_name = new_name.strip()

        if autodrive_data is None or not new_name or new_name == old_name:
            return False

        if new_name in autodrive_data.marker_group_names():
            self.status_changed.emit(tr("The marker group “{name}” already exists", name=new_name))
            return False

        self.edit_history.push(RenameMarkerGroupCommand(autodrive_data, old_name, new_name))

        if self.last_group == old_name:
            self.last_group = new_name

        self.status_changed.emit(
            tr("Marker group “{old}” renamed to “{new}”", old=old_name, new=new_name)
        )

        return True

    def delete_group(self, name: str) -> bool:
        autodrive_data = self.autodrive_data_provider()

        if autodrive_data is None:
            return False

        if autodrive_data.markers_in_group(name):
            self.status_changed.emit(
                tr("The marker group “{name}” still contains markers", name=name)
            )
            return False

        if autodrive_data.find_marker_group(name) is None:
            return False

        self.edit_history.push(DeleteMarkerGroupCommand(autodrive_data, name))
        self.status_changed.emit(tr("Marker group “{name}” deleted", name=name))

        return True

    def _pick_up_marker(self, autodrive_data: AutoDriveData, node_id: int) -> bool:
        marker = autodrive_data.get_marker(node_id)

        if marker is None:
            self.status_changed.emit(tr("Node {node} has no marker", node=node_id))
            return False

        if self._selection_before_move is None:
            self._selection_before_move = (
                self.node_selection.selected_node_ids,
                self.node_selection.primary_node_id,
            )

        # The picked-up marker's node is shown as selected while moving.
        self.move_source_id = node_id
        self.node_selection.replace({node_id}, node_id)
        self.status_changed.emit(
            tr("Marker “{name}” picked – now click the target node", name=marker.name)
        )

        return True

    def reset_move(self):
        """Forgets a picked-up marker without touching the selection, e.g.
        when other data is loaded."""

        self.move_source_id = None
        self._selection_before_move = None

    def _restore_selection(self):
        if self._selection_before_move is None:
            return

        node_ids, primary_node_id = self._selection_before_move
        self._selection_before_move = None

        autodrive_data = self.autodrive_data_provider()
        existing = autodrive_data.nodes if autodrive_data is not None else {}

        self.node_selection.replace(
            {node_id for node_id in node_ids if node_id in existing}, primary_node_id
        )

    def _node_at(self, view_position: QPoint) -> tuple[AutoDriveData, int] | None:
        autodrive_data = self.autodrive_data_provider()

        if autodrive_data is None or self.edit_history.history_locked:
            return None

        clicked_node = self.selection_coordinator.get_node_at(view_position)

        if clicked_node is None:
            return None

        return autodrive_data, clicked_node.node_id

    def _suggested_group(self, autodrive_data: AutoDriveData) -> str:
        groups = autodrive_data.marker_group_names()

        if self.last_group in groups or not groups:
            return self.last_group

        return self.DEFAULT_GROUP if self.DEFAULT_GROUP in groups else groups[0]

    @staticmethod
    def _taken_names(
        autodrive_data: AutoDriveData, except_node_id: int | None = None
    ) -> set[tuple[str, str]]:
        """Names are unique within a group, not across groups."""

        return {
            (marker.name, marker.group)
            for node_id, marker in autodrive_data.markers.items()
            if node_id != except_node_id
        }
