from autodrive.models import (
    REGULAR_FLAG,
    AutoDriveData
)

from editing.edit_command import (
    DataChange,
    EditCommand
)


class SetNodeFlagsCommand(EditCommand):
    """Sets the flag (regular or subprio) of one or more nodes."""

    def __init__(
        self,
        autodrive_data: AutoDriveData,
        node_ids,
        flag: int
    ):
        node_ids = frozenset(
            int(node_id)
            for node_id in node_ids
        )

        if not node_ids:
            raise ValueError(
                "Es wurden keine Nodes angegeben."
            )

        for node_id in node_ids:
            if node_id not in autodrive_data.nodes:
                raise ValueError(
                    f"Die Node-ID {node_id} "
                    f"ist nicht vorhanden."
                )

        flag = int(
            flag
        )

        type_name = (
            "Regular"
            if flag == REGULAR_FLAG
            else "Subprio"
        )

        super().__init__(
            f"Node auf {type_name} setzen"
            if len(node_ids) == 1
            else f"{len(node_ids)} Nodes auf {type_name} setzen",
            autodrive_data
        )

        self.flag = flag

        self.old_flags = {
            node_id: autodrive_data.nodes[node_id].flag
            for node_id in node_ids
        }

        self.setObsolete(
            all(
                old_flag == flag
                for old_flag in self.old_flags.values()
            )
        )

    def apply(self) -> DataChange:
        return self._set_flags(
            {
                node_id: self.flag
                for node_id in self.old_flags
            }
        )

    def revert(self) -> DataChange:
        return self._set_flags(
            self.old_flags
        )

    def _set_flags(
        self,
        flags: dict[int, int]
    ) -> DataChange:
        for node_id, flag in flags.items():
            self.autodrive_data.nodes[
                node_id
            ].flag = flag

        return DataChange(
            changed_flag_node_ids=frozenset(
                flags
            )
        )
