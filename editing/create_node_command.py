from autodrive.models import REGULAR_FLAG, AutoDriveData, NodeData

from editing.edit_command import DataChange, EditCommand


class CreateNodeCommand(EditCommand):
    """Adds one new, unconnected node."""

    def __init__(
        self,
        autodrive_data: AutoDriveData,
        node_id: int,
        x: float,
        y: float,
        z: float,
        flag: int = 0,
    ):
        super().__init__(
            "Node erstellen" if int(flag) == REGULAR_FLAG else "Subprio-Node erstellen",
            autodrive_data,
        )

        node_id = int(node_id)

        if node_id in autodrive_data.nodes:
            raise ValueError(f"Die Node-ID {node_id} ist bereits vorhanden.")

        self.node = NodeData(node_id=node_id, x=float(x), y=float(y), z=float(z), flag=int(flag))

    def apply(self) -> DataChange:
        self.autodrive_data.add_node(self.node)

        return DataChange(added_node_ids=frozenset({self.node.node_id}))

    def revert(self) -> DataChange:
        del self.autodrive_data.nodes[self.node.node_id]

        return DataChange(removed_node_ids=frozenset({self.node.node_id}))
