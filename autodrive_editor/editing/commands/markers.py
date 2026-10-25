"""Undoable edits of markers and marker groups.

New markers are added at the end, so the numbers of existing markers
stay the same (savegame configs number markers by their order, and
vehicles refer to these numbers as parking destination).
"""

from autodrive_editor.editing.commands.edit_command import DataChange, EditCommand
from autodrive_editor.model.autodrive_data import AutoDriveData, MarkerData, MarkerGroup


def _require_marker(autodrive_data: AutoDriveData, node_id: int) -> MarkerData:
    marker = autodrive_data.get_marker(node_id)

    if marker is None:
        raise ValueError(f"Node {node_id} hat keinen Marker.")

    return marker


class GroupCreation:
    """Adds a marker group if it does not exist yet, and removes it again
    on undo."""

    def __init__(self, autodrive_data: AutoDriveData, group_name: str):
        self.autodrive_data = autodrive_data
        self.group_name = group_name
        self.created: MarkerGroup | None = None

    def apply(self) -> bool:
        if self.autodrive_data.find_marker_group(self.group_name) is not None:
            return False

        self.created = MarkerGroup(self.group_name, self.autodrive_data.next_marker_group_id())
        self.autodrive_data.marker_groups.append(self.created)

        return True

    def revert(self) -> bool:
        if self.created is None:
            return False

        self.autodrive_data.marker_groups.remove(self.created)
        self.created = None

        return True


class AddMarkerCommand(EditCommand):
    """Adds a marker at the end of the marker list. A new group name
    creates the group."""

    def __init__(self, autodrive_data: AutoDriveData, node_id: int, name: str, group: str):
        super().__init__("Marker hinzufügen", autodrive_data)

        node_id = int(node_id)

        if node_id not in autodrive_data.nodes:
            raise ValueError(f"Die Node-ID {node_id} ist nicht vorhanden.")

        if node_id in autodrive_data.markers:
            raise ValueError(f"Node {node_id} hat bereits einen Marker.")

        self.marker = MarkerData(node_id=node_id, name=name, group=group)
        self._group = GroupCreation(autodrive_data, group)

    def apply(self) -> DataChange:
        self.autodrive_data.add_marker(self.marker)
        groups_changed = self._group.apply()

        return DataChange(
            changed_marker_node_ids=frozenset({self.marker.node_id}),
            marker_groups_changed=groups_changed,
        )

    def revert(self) -> DataChange:
        self.autodrive_data.remove_marker(self.marker.node_id)
        groups_changed = self._group.revert()

        return DataChange(
            changed_marker_node_ids=frozenset({self.marker.node_id}),
            marker_groups_changed=groups_changed,
        )


class EditMarkerCommand(EditCommand):
    """Changes a marker's name and group."""

    def __init__(self, autodrive_data: AutoDriveData, node_id: int, name: str, group: str):
        super().__init__("Marker bearbeiten", autodrive_data)

        self.marker = _require_marker(autodrive_data, int(node_id))

        self.old_values = (self.marker.name, self.marker.group)
        self.new_values = (name, group)

        self._group = GroupCreation(autodrive_data, group)

        self.setObsolete(self.old_values == self.new_values)

    def apply(self) -> DataChange:
        self.marker.name, self.marker.group = self.new_values

        return self._change(self._group.apply())

    def revert(self) -> DataChange:
        self.marker.name, self.marker.group = self.old_values

        return self._change(self._group.revert())

    def _change(self, groups_changed: bool) -> DataChange:
        return DataChange(
            changed_marker_node_ids=frozenset({self.marker.node_id}),
            marker_groups_changed=groups_changed,
        )


class DeleteMarkerCommand(EditCommand):
    """Removes a marker; the node stays. Its group stays as well, even if
    it becomes empty."""

    def __init__(self, autodrive_data: AutoDriveData, node_id: int):
        super().__init__("Marker löschen", autodrive_data)

        self.node_id = int(node_id)
        _require_marker(autodrive_data, self.node_id)

        self._removed: tuple[int, MarkerData] | None = None

    def apply(self) -> DataChange:
        self._removed = self.autodrive_data.remove_marker(self.node_id)

        return DataChange(changed_marker_node_ids=frozenset({self.node_id}))

    def revert(self) -> DataChange:
        position, marker = self._removed
        self.autodrive_data.add_marker(marker, position)

        return DataChange(changed_marker_node_ids=frozenset({self.node_id}))


class MoveMarkerCommand(EditCommand):
    """Attaches a marker to another node without changing its number."""

    def __init__(self, autodrive_data: AutoDriveData, from_node_id: int, to_node_id: int):
        super().__init__("Marker verschieben", autodrive_data)

        self.from_node_id = int(from_node_id)
        self.to_node_id = int(to_node_id)

        _require_marker(autodrive_data, self.from_node_id)

        if self.to_node_id not in autodrive_data.nodes:
            raise ValueError(f"Die Node-ID {self.to_node_id} ist nicht vorhanden.")

        if self.to_node_id in autodrive_data.markers:
            raise ValueError(f"Node {self.to_node_id} hat bereits einen Marker.")

    def apply(self) -> DataChange:
        self.autodrive_data.move_marker(self.from_node_id, self.to_node_id)

        return self._change()

    def revert(self) -> DataChange:
        self.autodrive_data.move_marker(self.to_node_id, self.from_node_id)

        return self._change()

    def _change(self) -> DataChange:
        return DataChange(changed_marker_node_ids=frozenset({self.from_node_id, self.to_node_id}))


class RenameMarkerGroupCommand(EditCommand):
    """Renames a group and moves all its markers along."""

    def __init__(self, autodrive_data: AutoDriveData, old_name: str, new_name: str):
        super().__init__("Markergruppe umbenennen", autodrive_data)

        if old_name not in autodrive_data.marker_group_names():
            raise ValueError(f"Die Markergruppe „{old_name}“ ist nicht vorhanden.")

        if new_name != old_name and new_name in autodrive_data.marker_group_names():
            raise ValueError(f"Die Markergruppe „{new_name}“ ist bereits vorhanden.")

        self.old_name = old_name
        self.new_name = new_name

        self.node_ids = frozenset(
            marker.node_id for marker in autodrive_data.markers_in_group(old_name)
        )

        self.setObsolete(old_name == new_name)

    def apply(self) -> DataChange:
        return self._rename(self.old_name, self.new_name)

    def revert(self) -> DataChange:
        return self._rename(self.new_name, self.old_name)

    def _rename(self, current: str, new: str) -> DataChange:
        group = self.autodrive_data.find_marker_group(current)

        if group is not None:
            group.name = new

        for node_id in self.node_ids:
            self.autodrive_data.markers[node_id].group = new

        return DataChange(changed_marker_node_ids=self.node_ids, marker_groups_changed=True)


class DeleteMarkerGroupCommand(EditCommand):
    """Removes an empty group from the group list."""

    def __init__(self, autodrive_data: AutoDriveData, name: str):
        super().__init__("Markergruppe löschen", autodrive_data)

        group = autodrive_data.find_marker_group(name)

        if group is None:
            raise ValueError(f"Die Markergruppe „{name}“ ist nicht vorhanden.")

        if autodrive_data.markers_in_group(name):
            raise ValueError(f"Die Markergruppe „{name}“ enthält noch Marker.")

        self.group = group
        self.position = autodrive_data.marker_groups.index(group)

    def apply(self) -> DataChange:
        self.autodrive_data.marker_groups.remove(self.group)

        return DataChange(marker_groups_changed=True)

    def revert(self) -> DataChange:
        self.autodrive_data.marker_groups.insert(self.position, self.group)

        return DataChange(marker_groups_changed=True)
