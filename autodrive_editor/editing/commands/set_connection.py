from autodrive_editor.editing.commands.edit_command import DataChange, EditCommand
from autodrive_editor.model.autodrive_data import AutoDriveData
from autodrive_editor.model.connections import (
    NO_CONNECTION,
    ConnectionState,
    read_connection_state,
)


class SetConnectionCommand(EditCommand):
    """Sets the connection between two nodes to a given state, which
    creates, changes or removes it."""

    def __init__(
        self,
        autodrive_data: AutoDriveData,
        source_id: int,
        target_id: int,
        new_state: ConnectionState,
    ):
        source_id = int(source_id)
        target_id = int(target_id)

        for node_id in (source_id, target_id):
            if node_id not in autodrive_data.nodes:
                raise ValueError(f"Die Node-ID {node_id} ist nicht vorhanden.")

        if source_id == target_id:
            raise ValueError("Eine Node kann nicht mit sich selbst verbunden werden.")

        old_state = read_connection_state(autodrive_data, source_id, target_id)

        if new_state == NO_CONNECTION:
            text = "Connection entfernen"

        elif old_state == NO_CONNECTION:
            text = "Connection erstellen"

        else:
            text = "Connection ändern"

        super().__init__(text, autodrive_data)

        self.source_id = source_id
        self.target_id = target_id
        self.old_state = old_state
        self.new_state = tuple(bool(value) for value in new_state)

        self.setObsolete(self.old_state == self.new_state)

    def apply(self) -> DataChange:
        return self._set_state(self.new_state)

    def revert(self) -> DataChange:
        return self._set_state(self.old_state)

    def _set_state(self, state: ConnectionState) -> DataChange:
        source = self.autodrive_data.nodes[self.source_id]

        target = self.autodrive_data.nodes[self.target_id]

        entries = (
            (source.outgoing, self.target_id),
            (source.incoming, self.target_id),
            (target.outgoing, self.source_id),
            (target.incoming, self.source_id),
        )

        for (connections, node_id), present in zip(entries, state):
            if present:
                connections.add(node_id)

            else:
                connections.discard(node_id)

        return DataChange(connection_node_ids=frozenset((self.source_id, self.target_id)))
