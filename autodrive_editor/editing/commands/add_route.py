from autodrive_editor.editing.commands.edit_command import DataChange, EditCommand
from autodrive_editor.model.autodrive_data import AutoDriveData, NodeData
from autodrive_editor.model.connections import (
    NO_CONNECTION,
    ConnectionState,
    read_connection_state,
    write_connection_state,
)


class AddRouteCommand(EditCommand):
    """Adds new nodes and sets the connections of a route, each pair to its own state, as one
    undo step. Used for found routes, which may also turn existing connections into dual ones."""

    def __init__(
        self,
        text: str,
        autodrive_data: AutoDriveData,
        new_nodes: list[NodeData],
        connections: list[tuple[int, int, ConnectionState]],
    ):
        super().__init__(text, autodrive_data)

        new_ids = {node.node_id for node in new_nodes}

        if new_ids & set(autodrive_data.nodes):
            raise ValueError("New nodes need new node IDs.")

        for source, target, _ in connections:
            if source == target:
                raise ValueError("A node cannot be connected to itself.")

            for node_id in (source, target):
                if node_id not in new_ids and node_id not in autodrive_data.nodes:
                    raise ValueError(f"Node ID {node_id} does not exist.")

        self.new_nodes = list(new_nodes)
        self.new_ids = frozenset(new_ids)
        self.connections = [
            (source, target, tuple(bool(value) for value in state))
            for source, target, state in connections
        ]
        self.existing_ids = (
            frozenset(node_id for source, target, _ in connections for node_id in (source, target))
            - self.new_ids
        )
        self.old_states = [
            read_connection_state(autodrive_data, source, target)
            if source in autodrive_data.nodes and target in autodrive_data.nodes
            else NO_CONNECTION
            for source, target, _ in connections
        ]

    def apply(self) -> DataChange:
        for node in self.new_nodes:
            self.autodrive_data.add_node(node)

        for source, target, state in self.connections:
            write_connection_state(self.autodrive_data, source, target, state)

        return DataChange(added_node_ids=self.new_ids, connection_node_ids=self.existing_ids)

    def revert(self) -> DataChange:
        for (source, target, _), old_state in reversed(
            list(zip(self.connections, self.old_states, strict=True))
        ):
            write_connection_state(self.autodrive_data, source, target, old_state)

        for node in self.new_nodes:
            del self.autodrive_data.nodes[node.node_id]

        return DataChange(removed_node_ids=self.new_ids, connection_node_ids=self.existing_ids)
