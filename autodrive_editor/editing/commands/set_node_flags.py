from autodrive_editor.editing.commands.edit_command import DataChange, EditCommand
from autodrive_editor.i18n import tr
from autodrive_editor.model.autodrive_data import REGULAR_FLAG, AutoDriveData


class SetNodeFlagsCommand(EditCommand):
    """Sets the flag (regular or subprio) of one or more nodes."""

    def __init__(self, autodrive_data: AutoDriveData, node_ids, flag: int):
        node_ids = frozenset(int(node_id) for node_id in node_ids)

        if not node_ids:
            raise ValueError("No nodes were given.")

        for node_id in node_ids:
            if node_id not in autodrive_data.nodes:
                raise ValueError(f"Node ID {node_id} does not exist.")

        flag = int(flag)

        type_name = "Regular" if flag == REGULAR_FLAG else "Subprio"

        super().__init__(
            tr("Set node to {type}", type=type_name)
            if len(node_ids) == 1
            else tr("Set {count} nodes to {type}", count=len(node_ids), type=type_name),
            autodrive_data,
        )

        self.flag = flag

        self.old_flags = {node_id: autodrive_data.nodes[node_id].flag for node_id in node_ids}

        self.setObsolete(all(old_flag == flag for old_flag in self.old_flags.values()))

    def apply(self) -> DataChange:
        return self._set_flags({node_id: self.flag for node_id in self.old_flags})

    def revert(self) -> DataChange:
        return self._set_flags(self.old_flags)

    def _set_flags(self, flags: dict[int, int]) -> DataChange:
        for node_id, flag in flags.items():
            self.autodrive_data.nodes[node_id].flag = flag

        return DataChange(changed_flag_node_ids=frozenset(flags))
