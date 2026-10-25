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
from autodrive_editor.model.autodrive_data import AutoDriveData, MarkerData
from autodrive_editor.selection.selection_coordinator import SelectionCoordinator

# Asks the user for a marker's name and group. Arguments: dialog title,
# the marker being edited (None for a new one) or the suggested group,
# all group names, and the names other markers already use. Returns
# (name, group), or None if cancelled.
MarkerRequest = Callable[[str, MarkerData | None, str, list[str], set[str]], tuple[str, str] | None]


class MarkerOperation(QObject):
    """Adds, edits, moves and deletes markers and renames or deletes
    marker groups, all through the undo history."""

    status_changed = Signal(str)

    DEFAULT_GROUP = "All"

    def __init__(
        self,
        selection_coordinator: SelectionCoordinator,
        edit_history: EditHistory,
        autodrive_data_provider: Callable[[], AutoDriveData | None],
        ask_marker: MarkerRequest,
        parent=None,
    ):
        super().__init__(parent)

        self.selection_coordinator = selection_coordinator
        self.edit_history = edit_history
        self.autodrive_data_provider = autodrive_data_provider
        self.ask_marker = ask_marker

        # New markers suggest the group used last.
        self.last_group = self.DEFAULT_GROUP

        # Node whose marker the move tool has picked up.
        self.move_source_id: int | None = None

    def add_at(self, view_position: QPoint) -> bool:
        target = self._node_at(view_position)

        if target is None:
            return False

        autodrive_data, node_id = target
        existing = autodrive_data.get_marker(node_id)

        if existing is not None:
            self.status_changed.emit(f"Node {node_id} hat bereits den Marker „{existing.name}“")
            return False

        values = self.ask_marker(
            "Marker hinzufügen",
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
        self.status_changed.emit(f"Marker „{name}“ hinzugefügt")

        return True

    def edit_at(self, view_position: QPoint) -> bool:
        target = self._node_at(view_position)

        if target is None:
            return False

        autodrive_data, node_id = target

        if autodrive_data.get_marker(node_id) is None:
            self.status_changed.emit(f"Node {node_id} hat keinen Marker")
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
            "Marker bearbeiten",
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
        self.status_changed.emit(f"Marker „{name}“ geändert")

        return True

    def delete_at(self, view_position: QPoint) -> bool:
        target = self._node_at(view_position)

        if target is None:
            return False

        autodrive_data, node_id = target
        marker = autodrive_data.get_marker(node_id)

        if marker is None:
            self.status_changed.emit(f"Node {node_id} hat keinen Marker")
            return False

        self.edit_history.push(DeleteMarkerCommand(autodrive_data, node_id))
        self.status_changed.emit(f"Marker „{marker.name}“ gelöscht")

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
            self.status_changed.emit(f"Node {node_id} hat bereits den Marker „{existing.name}“")
            return False

        marker = autodrive_data.get_marker(self.move_source_id)
        self.edit_history.push(MoveMarkerCommand(autodrive_data, self.move_source_id, node_id))
        self.move_source_id = None
        self.status_changed.emit(f"Marker „{marker.name}“ auf Node {node_id} verschoben")

        return True

    def cancel_move(self) -> bool:
        if self.move_source_id is None:
            return False

        self.move_source_id = None
        self.status_changed.emit("Marker verschieben abgebrochen")

        return True

    def rename_group(self, old_name: str, new_name: str) -> bool:
        autodrive_data = self.autodrive_data_provider()
        new_name = new_name.strip()

        if autodrive_data is None or not new_name or new_name == old_name:
            return False

        if new_name in autodrive_data.marker_group_names():
            self.status_changed.emit(f"Die Markergruppe „{new_name}“ gibt es bereits")
            return False

        self.edit_history.push(RenameMarkerGroupCommand(autodrive_data, old_name, new_name))

        if self.last_group == old_name:
            self.last_group = new_name

        self.status_changed.emit(f"Markergruppe „{old_name}“ in „{new_name}“ umbenannt")

        return True

    def delete_group(self, name: str) -> bool:
        autodrive_data = self.autodrive_data_provider()

        if autodrive_data is None:
            return False

        if autodrive_data.markers_in_group(name):
            self.status_changed.emit(f"Die Markergruppe „{name}“ enthält noch Marker")
            return False

        if autodrive_data.find_marker_group(name) is None:
            return False

        self.edit_history.push(DeleteMarkerGroupCommand(autodrive_data, name))
        self.status_changed.emit(f"Markergruppe „{name}“ gelöscht")

        return True

    def _pick_up_marker(self, autodrive_data: AutoDriveData, node_id: int) -> bool:
        marker = autodrive_data.get_marker(node_id)

        if marker is None:
            self.status_changed.emit(f"Node {node_id} hat keinen Marker")
            return False

        self.move_source_id = node_id
        self.status_changed.emit(f"Marker „{marker.name}“ gewählt – jetzt die Ziel-Node anklicken")

        return True

    def _node_at(self, view_position: QPoint) -> tuple[AutoDriveData, int] | None:
        autodrive_data = self.autodrive_data_provider()

        if autodrive_data is None or self.edit_history.history_locked:
            return None

        node_item = self.selection_coordinator.get_node_item_at(view_position)

        if node_item is None:
            return None

        return autodrive_data, node_item.node_id

    def _suggested_group(self, autodrive_data: AutoDriveData) -> str:
        groups = autodrive_data.marker_group_names()

        if self.last_group in groups or not groups:
            return self.last_group

        return self.DEFAULT_GROUP if self.DEFAULT_GROUP in groups else groups[0]

    @staticmethod
    def _taken_names(autodrive_data: AutoDriveData, except_node_id: int | None = None) -> set[str]:
        return {
            marker.name
            for node_id, marker in autodrive_data.markers.items()
            if node_id != except_node_id
        }
