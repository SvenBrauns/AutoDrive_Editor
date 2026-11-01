from autodrive_editor.editing.commands.edit_command import DataChange, EditCommand
from autodrive_editor.model.autodrive_data import AutoDriveData


class ReplaceNetworkCommand(EditCommand):
    """Replaces the whole network (nodes, markers, groups) with another one, e.g. a route loaded
    into the savegame. The data object stays the same, so everything holding it keeps working."""

    def __init__(self, autodrive_data: AutoDriveData, new_data: AutoDriveData, text: str):
        super().__init__(text, autodrive_data)

        self._old = _parts(autodrive_data)
        self._new = _parts(new_data)

    def apply(self) -> DataChange:
        return self._show(self._old, self._new)

    def revert(self) -> DataChange:
        return self._show(self._new, self._old)

    def _show(self, before, after) -> DataChange:
        nodes, markers, groups = after
        data = self.autodrive_data
        data.nodes.clear()
        data.nodes.update(nodes)
        data.markers.clear()
        data.markers.update(markers)
        data.marker_groups[:] = groups

        return DataChange(
            removed_node_ids=frozenset(before[0]),
            added_node_ids=frozenset(nodes),
            marker_groups_changed=True,
        )


def _parts(data: AutoDriveData):
    return dict(data.nodes), dict(data.markers), list(data.marker_groups)
