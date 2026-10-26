from itertools import pairwise

from autodrive_editor.editing.commands.edit_command import DataChange, EditCommand
from autodrive_editor.model.autodrive_data import AutoDriveData, NodeData
from autodrive_editor.model.connections import (
    NO_CONNECTION,
    ConnectionState,
    read_connection_state,
    write_connection_state,
)


class CreatePathCommand(EditCommand):
    """Adds a chain of new nodes and connects each point of the chain to
    the next one with the same connection state. The chain may start and
    end at existing nodes."""

    def __init__(
        self,
        text: str,
        autodrive_data: AutoDriveData,
        chain: list[int],
        new_nodes: list[NodeData],
        state: ConnectionState,
    ):
        super().__init__(text, autodrive_data)

        new_ids = {node.node_id for node in new_nodes}

        if new_ids & set(autodrive_data.nodes):
            raise ValueError("Neue Nodes brauchen neue Node-IDs.")

        if len(chain) < 2:
            raise ValueError("Eine Strecke braucht mindestens zwei Punkte.")

        for node_id in chain:
            if node_id not in new_ids and node_id not in autodrive_data.nodes:
                raise ValueError(f"Die Node-ID {node_id} ist nicht vorhanden.")

        self.pairs = list(pairwise(chain))

        if any(source == target for source, target in self.pairs):
            raise ValueError("Eine Node kann nicht mit sich selbst verbunden werden.")

        self.new_nodes = list(new_nodes)
        self.new_ids = frozenset(new_ids)
        self.existing_ids = frozenset(chain) - self.new_ids
        self.state = tuple(bool(value) for value in state)

        # Only a pair of two existing nodes can already be connected.
        self.old_states = [
            read_connection_state(autodrive_data, source, target)
            if source in self.existing_ids and target in self.existing_ids
            else NO_CONNECTION
            for source, target in self.pairs
        ]

    def apply(self) -> DataChange:
        for node in self.new_nodes:
            self.autodrive_data.add_node(node)

        for source, target in self.pairs:
            write_connection_state(self.autodrive_data, source, target, self.state)

        return DataChange(added_node_ids=self.new_ids, connection_node_ids=self.existing_ids)

    def revert(self) -> DataChange:
        pairs_with_states = zip(self.pairs, self.old_states, strict=True)

        for (source, target), old_state in reversed(list(pairs_with_states)):
            write_connection_state(self.autodrive_data, source, target, old_state)

        for node in self.new_nodes:
            del self.autodrive_data.nodes[node.node_id]

        return DataChange(removed_node_ids=self.new_ids, connection_node_ids=self.existing_ids)
