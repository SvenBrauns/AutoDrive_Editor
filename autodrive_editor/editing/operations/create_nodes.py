import math

from PySide6.QtCore import QPoint

from autodrive_editor.editing.commands.create_node import CreateNodeCommand
from autodrive_editor.editing.edit_context import EditContext, EditOperation
from autodrive_editor.i18n import tr
from autodrive_editor.model.autodrive_data import REGULAR_FLAG, AutoDriveData


class CreateNodesOperation(EditOperation):
    """Creates single unconnected nodes on the map."""

    def __init__(self, context: EditContext, parent=None):
        super().__init__(context, parent)

    def create_node_at(self, view_position: QPoint, flag: int = REGULAR_FLAG) -> int | None:
        """Creates a node with the given flag (regular or subprio) at
        the view position. Returns the new node id, or None if nothing
        was created."""

        autodrive_data = self.autodrive_data_provider()

        if autodrive_data is None:
            self.status_changed.emit(tr("Load an AutoDrive XML first"))
            return None

        if self.edit_history.history_locked:
            return None

        # Clicking an existing node does not create a second one there.
        if self.selection_coordinator.get_node_at(view_position) is not None:
            return None

        scene_position = self.view.mapToScene(view_position)

        x = scene_position.x()
        z = scene_position.y()

        if self.snap_point is not None:
            x, z = self.snap_point(x, z)

        node_id = self.next_node_id(autodrive_data)

        self.edit_history.push(
            CreateNodeCommand(
                autodrive_data,
                node_id=node_id,
                x=x,
                y=self.height_for_new_node(autodrive_data, x, z),
                z=z,
                flag=flag,
            )
        )

        self.status_changed.emit(
            tr("Node {node} created", node=node_id)
            if flag == REGULAR_FLAG
            else tr("Subprio node {node} created", node=node_id)
        )

        return node_id

    @staticmethod
    def next_node_id(autodrive_data: AutoDriveData) -> int:
        return max(autodrive_data.nodes, default=0) + 1

    def height_for_new_node(self, autodrive_data: AutoDriveData, x: float, z: float) -> float:
        """Terrain height from the heightmap, otherwise the height of
        the nearest node, otherwise 0."""

        if self.terrain_height_at is not None:
            terrain_height = self.terrain_height_at(x, z)

            if terrain_height is not None:
                return terrain_height

        nearest_node = min(
            autodrive_data.nodes.values(),
            key=lambda node: math.hypot(node.x - x, node.z - z),
            default=None,
        )

        if nearest_node is None:
            return 0.0

        return nearest_node.y
