from collections.abc import Callable

from PySide6.QtCore import QObject, QPoint, Signal

from autodrive_editor.editing.commands.set_connection import (
    CONNECTION_STATES,
    NO_CONNECTION,
    SetConnectionCommand,
    read_connection_state,
)
from autodrive_editor.editing.edit_history import EditCoordinator
from autodrive_editor.model.autodrive_data import AutoDriveData, NodeData
from autodrive_editor.rendering.connections.connection_data import ConnectionType
from autodrive_editor.selection.selection_coordinator import SelectionCoordinator

CONNECTION_TYPE_NAMES = {
    ConnectionType.REGULAR: "Regular",
    ConnectionType.DUAL: "Dual",
    ConnectionType.REVERSE: "Reverse",
}


class NodeConnectCoordinator(QObject):
    """Connects nodes by clicking them one after another.

    The first click picks the start node. Each further click on a node
    sets the connection from the start node to it and makes it the new
    start, so whole routes can be drawn. Clicking with the type the
    connection already has removes it. A click on empty map or Esc
    ends the chain.
    """

    status_changed = Signal(str)

    start_node_changed = Signal(object)

    def __init__(
        self,
        selection_coordinator: SelectionCoordinator,
        edit_coordinator: EditCoordinator,
        autodrive_data_provider: Callable[[], AutoDriveData | None],
        parent=None,
    ):
        super().__init__(parent)

        self.selection_coordinator = selection_coordinator
        self.edit_coordinator = edit_coordinator
        self.autodrive_data_provider = autodrive_data_provider

        self._start_node_id: int | None = None

    @property
    def start_node(self) -> NodeData | None:
        """The node the next connection starts at, if it still
        exists."""

        if self._start_node_id is None:
            return None

        autodrive_data = self.autodrive_data_provider()

        if autodrive_data is None:
            return None

        return autodrive_data.get_node(self._start_node_id)

    def click(self, view_position: QPoint, connection_type: ConnectionType):
        autodrive_data = self.autodrive_data_provider()

        node_item = self.selection_coordinator.get_node_item_at(view_position)

        if autodrive_data is None or node_item is None:
            if self.start_node is not None:
                self.status_changed.emit("Verbinden beendet")

            self.end_chain()
            return

        clicked_id = node_item.node_id
        start_node = self.start_node

        if start_node is None:
            self._set_start(clicked_id)

            self.status_changed.emit(f"Start: Node {clicked_id}. Ziel-Node anklicken")
            return

        if clicked_id == start_node.node_id:
            return

        if self.edit_coordinator.history_locked:
            return

        self._connect(autodrive_data, start_node.node_id, clicked_id, connection_type)

        self._set_start(clicked_id)

    def end_chain(self) -> bool:
        """Forgets the start node. Returns True if there was one."""

        had_start = self._start_node_id is not None

        self._set_start(None)

        return had_start

    def _connect(
        self,
        autodrive_data: AutoDriveData,
        source_id: int,
        target_id: int,
        connection_type: ConnectionType,
    ):
        wanted_state = CONNECTION_STATES[connection_type]

        current_state = read_connection_state(autodrive_data, source_id, target_id)

        # Clicking with the type the connection already has removes it.
        removing = current_state == wanted_state

        self.edit_coordinator.push(
            SetConnectionCommand(
                autodrive_data, source_id, target_id, NO_CONNECTION if removing else wanted_state
            )
        )

        type_name = CONNECTION_TYPE_NAMES[connection_type]

        if removing:
            self.status_changed.emit(f"{type_name}-Connection {source_id} → {target_id} entfernt")

        else:
            self.status_changed.emit(f"{type_name}-Connection {source_id} → {target_id} gesetzt")

    def _set_start(self, node_id: int | None):
        if node_id == self._start_node_id:
            return

        self._start_node_id = node_id

        self.start_node_changed.emit(node_id)
