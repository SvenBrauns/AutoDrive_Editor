from collections.abc import Callable

from PySide6.QtCore import QPoint, Signal

from autodrive_editor.editing.commands.add_route import AddRouteCommand
from autodrive_editor.editing.commands.set_connection import SetConnectionCommand
from autodrive_editor.editing.edit_context import EditContext, EditOperation
from autodrive_editor.editing.road_edits import split_connection
from autodrive_editor.i18n import tr
from autodrive_editor.model.autodrive_data import REGULAR_FLAG, AutoDriveData, NodeData
from autodrive_editor.model.connections import (
    CONNECTION_STATES,
    NO_CONNECTION,
    ConnectionType,
    read_connection_state,
)

CONNECTION_TYPE_NAMES = {
    ConnectionType.REGULAR: "Regular",
    ConnectionType.DUAL: "Dual",
    ConnectionType.REVERSE: "Reverse",
}


class ConnectNodesOperation(EditOperation):
    """Connects nodes by clicking them one after another.

    The first click picks the start node. Each further click on a node
    sets the connection from the start node to it and makes it the new
    start, so whole routes can be drawn. Clicking with the type the
    connection already has removes it. A click on free ground creates
    a node there, a click on a connection inserts one into it; either
    is connected from the start and becomes the new start, so a road
    is drawn with one tool. Esc ends the chain.
    """

    start_node_changed = Signal(object)

    def __init__(
        self,
        context: EditContext,
        connection_at: Callable | None = None,
        height_for_new_node: Callable[[AutoDriveData, float, float], float] | None = None,
        parent=None,
    ):
        super().__init__(context, parent)

        self.connection_at = connection_at
        self.height_for_new_node = height_for_new_node
        # Type of the nodes created on free ground or in a connection.
        self.node_flag = REGULAR_FLAG
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

        if autodrive_data is None:
            self.end_chain()
            return

        clicked_node = self.selection_coordinator.get_node_at(view_position)

        if clicked_node is None:
            if not self.edit_history.history_locked:
                self._add_node(autodrive_data, view_position, connection_type)

            return

        clicked_id = clicked_node.node_id
        start_node = self.start_node

        if start_node is None:
            self._set_start(clicked_id)

            self.status_changed.emit(
                tr("Start: node {node}. Click the target node", node=clicked_id)
            )
            return

        if clicked_id == start_node.node_id:
            return

        if self.edit_history.history_locked:
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

        self.edit_history.push(
            SetConnectionCommand(
                autodrive_data, source_id, target_id, NO_CONNECTION if removing else wanted_state
            )
        )

        type_name = CONNECTION_TYPE_NAMES[connection_type]

        if removing:
            self.status_changed.emit(
                tr(
                    "{type} connection {source} → {target} removed",
                    type=type_name,
                    source=source_id,
                    target=target_id,
                )
            )

        else:
            self.status_changed.emit(
                tr(
                    "{type} connection {source} → {target} set",
                    type=type_name,
                    source=source_id,
                    target=target_id,
                )
            )

    def _add_node(
        self, autodrive_data: AutoDriveData, view_position: QPoint, connection_type: ConnectionType
    ):
        """Creates a node at the click, inside the connection there if there is one, connects it
        from the start node and makes it the new start. One undo step."""

        start_node = self.start_node
        node_id = max(autodrive_data.nodes, default=0) + 1
        state = CONNECTION_STATES[connection_type]
        to_new = [] if start_node is None else [(start_node.node_id, node_id, state)]
        text = tr("Add connected node")
        scene_position = self.view.mapToScene(view_position)
        x, z = scene_position.x(), scene_position.y()
        connection = self.connection_at(view_position) if self.connection_at else None

        if connection is not None:
            command = split_connection(
                autodrive_data,
                connection.source_id,
                connection.target_id,
                x,
                z,
                node_id,
                self.node_flag,
                text,
                to_new,
            )

        else:
            if self.snap_point is not None:
                x, z = self.snap_point(x, z)

            y = self.height_for_new_node(autodrive_data, x, z) if self.height_for_new_node else 0.0
            node = NodeData(node_id, x, y, z, self.node_flag)
            command = AddRouteCommand(text, autodrive_data, [node], to_new)

        self.edit_history.push(command)
        self._set_start(node_id)
        self.status_changed.emit(
            tr("Node {node} added. Click the next point, Esc finishes", node=node_id)
        )

    def _set_start(self, node_id: int | None):
        if node_id == self._start_node_id:
            return

        self._start_node_id = node_id

        self.start_node_changed.emit(node_id)
