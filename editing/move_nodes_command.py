from autodrive.models import AutoDriveData

from editing.edit_command import (
    DataChange,
    EditCommand
)


NodePosition = tuple[float, float, float]


class MoveNodesCommand(EditCommand):
    """Moves one or more nodes to new x, y, z positions.

    Commands with the same merge_key are combined into one undo step,
    so a whole drag can be undone at once.
    """

    COMMAND_ID = 1001

    def __init__(
        self,
        autodrive_data: AutoDriveData,
        old_positions: dict[int, NodePosition],
        new_positions: dict[int, NodePosition],
        merge_key=None
    ):
        node_count = len(
            new_positions
        )

        super().__init__(
            "Node verschieben"
            if node_count == 1
            else f"{node_count} Nodes verschieben",
            autodrive_data
        )

        if set(old_positions) != set(new_positions):
            raise ValueError(
                "Alte und neue Positionen müssen "
                "dieselben Nodes enthalten."
            )

        if not new_positions:
            raise ValueError(
                "Es wurden keine Nodes zum "
                "Verschieben angegeben."
            )

        for node_id in new_positions:
            if node_id not in autodrive_data.nodes:
                raise ValueError(
                    f"Die Node-ID {node_id} "
                    f"ist nicht vorhanden."
                )

        self.old_positions = self._normalize_positions(
            old_positions
        )

        self.new_positions = self._normalize_positions(
            new_positions
        )

        self.merge_key = merge_key

        self._update_obsolete_state()

    def id(self) -> int:
        if self.merge_key is None:
            return -1

        return self.COMMAND_ID

    def mergeWith(
        self,
        other
    ) -> bool:
        if not isinstance(
            other,
            MoveNodesCommand
        ):
            return False

        if (
            self.merge_key is None
            or other.merge_key != self.merge_key
            or other.autodrive_data is not self.autodrive_data
            or set(other.new_positions)
            != set(self.new_positions)
        ):
            return False

        self.new_positions = dict(
            other.new_positions
        )

        self._update_obsolete_state()

        return True

    def apply(self) -> DataChange:
        return self._set_positions(
            self.new_positions
        )

    def revert(self) -> DataChange:
        return self._set_positions(
            self.old_positions
        )

    def _set_positions(
        self,
        positions: dict[int, NodePosition]
    ) -> DataChange:
        for node_id, (x, y, z) in positions.items():
            node = self.autodrive_data.nodes[
                node_id
            ]

            node.x = x
            node.y = y
            node.z = z

        return DataChange(
            changed_node_ids=frozenset(
                positions
            )
        )

    def _update_obsolete_state(self):
        # Qt drops obsolete commands, so a move that ends where it
        # started does not leave an empty undo step behind.
        self.setObsolete(
            self.old_positions
            == self.new_positions
        )

    @staticmethod
    def _normalize_positions(
        positions: dict[int, NodePosition]
    ) -> dict[int, NodePosition]:
        return {
            int(node_id): (
                float(x),
                float(y),
                float(z)
            )
            for node_id, (x, y, z) in positions.items()
        }
