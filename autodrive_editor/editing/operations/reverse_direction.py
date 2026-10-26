from collections.abc import Callable

from PySide6.QtCore import QObject, QPoint, Signal

from autodrive_editor.editing.commands.reverse_connections import ReverseConnectionsCommand
from autodrive_editor.editing.edit_history import EditHistory
from autodrive_editor.i18n import tr
from autodrive_editor.model.autodrive_data import AutoDriveData
from autodrive_editor.model.connections import ConnectionType, is_dual_connection
from autodrive_editor.rendering.connections.connection_data import ConnectionData
from autodrive_editor.selection.node_selection import NodeSelection


class ReverseDirectionOperation(QObject):
    """Flips the direction of connections. Dual connections have no
    direction and stay unchanged."""

    status_changed = Signal(str)

    def __init__(
        self,
        connection_at: Callable[[QPoint], ConnectionData | None],
        node_selection: NodeSelection,
        edit_history: EditHistory,
        autodrive_data_provider: Callable[[], AutoDriveData | None],
        parent=None,
    ):
        super().__init__(parent)

        self.connection_at = connection_at
        self.node_selection = node_selection
        self.edit_history = edit_history
        self.autodrive_data_provider = autodrive_data_provider

    def reverse_at(self, view_position: QPoint) -> bool:
        """Flips the connection at the view position. If both its nodes
        are selected, all connections inside the selection flip."""

        autodrive_data = self.autodrive_data_provider()

        if autodrive_data is None or self.edit_history.history_locked:
            return False

        connection = self.connection_at(view_position)

        if connection is None:
            return False

        selected = self.node_selection.selected_node_ids

        if {connection.source_id, connection.target_id} <= selected:
            pairs = self._directed_pairs(autodrive_data, selected)
        elif connection.connection_type == ConnectionType.DUAL:
            pairs = set()
        else:
            pairs = {(connection.source_id, connection.target_id)}

        if not pairs:
            self.status_changed.emit(tr("Dual connections have no direction"))
            return False

        self.edit_history.push(ReverseConnectionsCommand(autodrive_data, pairs))

        self.status_changed.emit(
            tr("Direction reversed")
            if len(pairs) == 1
            else tr("{count} directions reversed", count=len(pairs))
        )

        return True

    @staticmethod
    def _directed_pairs(autodrive_data: AutoDriveData, node_ids: set[int]) -> set[tuple[int, int]]:
        """Node pairs inside node_ids with a regular or reverse connection."""

        pairs = set()

        for node_id in node_ids:
            node = autodrive_data.nodes.get(node_id)

            if node is None:
                continue

            for target_id in node.outgoing & node_ids:
                if not is_dual_connection(node, autodrive_data.nodes[target_id]):
                    pairs.add(tuple(sorted((node_id, target_id))))

        return pairs
