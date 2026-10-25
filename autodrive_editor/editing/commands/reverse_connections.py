from autodrive_editor.editing.commands.edit_command import DataChange, EditCommand
from autodrive_editor.model.autodrive_data import AutoDriveData
from autodrive_editor.model.connections import ConnectionState, read_connection_state


def reversed_state(state: ConnectionState) -> ConnectionState:
    """The same connection with source and target swapped. A regular or
    reverse connection keeps its type and points the other way."""

    a_out_b, a_in_b, b_out_a, b_in_a = state

    return (b_out_a, b_in_a, a_out_b, a_in_b)


class ReverseConnectionsCommand(EditCommand):
    """Flips the direction of the connections between the given node
    pairs in one undo step."""

    def __init__(self, autodrive_data: AutoDriveData, node_pairs):
        pairs = sorted({tuple(sorted((int(a), int(b)))) for a, b in node_pairs})

        if not pairs:
            raise ValueError("Es wurden keine Connections angegeben.")

        super().__init__(
            "Richtung umkehren" if len(pairs) == 1 else f"{len(pairs)} Richtungen umkehren",
            autodrive_data,
        )

        self.old_states = {pair: read_connection_state(autodrive_data, *pair) for pair in pairs}

    def apply(self) -> DataChange:
        return self._set_states(
            {pair: reversed_state(state) for pair, state in self.old_states.items()}
        )

    def revert(self) -> DataChange:
        return self._set_states(self.old_states)

    def _set_states(self, states: dict[tuple[int, int], ConnectionState]) -> DataChange:
        for (a_id, b_id), state in states.items():
            a = self.autodrive_data.nodes[a_id]
            b = self.autodrive_data.nodes[b_id]

            entries = (
                (a.outgoing, b_id),
                (a.incoming, b_id),
                (b.outgoing, a_id),
                (b.incoming, a_id),
            )

            for (connections, node_id), present in zip(entries, state, strict=True):
                if present:
                    connections.add(node_id)
                else:
                    connections.discard(node_id)

        return DataChange(
            connection_node_ids=frozenset(node_id for pair in states for node_id in pair)
        )
