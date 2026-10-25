import math

from collections.abc import Callable

from PySide6.QtCore import (
    QObject,
    QPoint,
    Signal
)

from autodrive.models import (
    REGULAR_FLAG,
    AutoDriveData
)
from editing.create_node_command import CreateNodeCommand
from editing.edit_coordinator import EditCoordinator
from editing.terrain_follower import TerrainHeightProvider
from selection.selection_coordinator import (
    SelectionCoordinator
)
from ui.map_view import MapView


class NodeCreateCoordinator(QObject):
    """Creates single unconnected nodes on the map."""

    status_changed = Signal(
        str
    )

    def __init__(
        self,
        view: MapView,
        selection_coordinator: SelectionCoordinator,
        edit_coordinator: EditCoordinator,
        autodrive_data_provider: Callable[
            [],
            AutoDriveData | None
        ],
        terrain_height_at: TerrainHeightProvider | None = None,
        parent=None
    ):
        super().__init__(
            parent
        )

        self.view = view
        self.selection_coordinator = selection_coordinator
        self.edit_coordinator = edit_coordinator
        self.autodrive_data_provider = (
            autodrive_data_provider
        )
        self.terrain_height_at = terrain_height_at

    def create_node_at(
        self,
        view_position: QPoint,
        flag: int = REGULAR_FLAG
    ) -> int | None:
        """Creates a node with the given flag (regular or subprio) at
        the view position. Returns the new node id, or None if nothing
        was created."""

        autodrive_data = self.autodrive_data_provider()

        if autodrive_data is None:
            self.status_changed.emit(
                "Zuerst eine AutoDrive-XML laden"
            )
            return None

        if self.edit_coordinator.history_locked:
            return None

        # Clicking an existing node does not create a second one there.
        if (
            self.selection_coordinator.get_node_item_at(
                view_position
            )
            is not None
        ):
            return None

        scene_position = self.view.mapToScene(
            view_position
        )

        x = scene_position.x()
        z = scene_position.y()

        node_id = self.next_node_id(
            autodrive_data
        )

        self.edit_coordinator.push(
            CreateNodeCommand(
                autodrive_data,
                node_id=node_id,
                x=x,
                y=self.height_for_new_node(
                    autodrive_data,
                    x,
                    z
                ),
                z=z,
                flag=flag
            )
        )

        self.status_changed.emit(
            f"Node {node_id} erstellt"
            if flag == REGULAR_FLAG
            else f"Subprio-Node {node_id} erstellt"
        )

        return node_id

    @staticmethod
    def next_node_id(
        autodrive_data: AutoDriveData
    ) -> int:
        return max(
            autodrive_data.nodes,
            default=0
        ) + 1

    def height_for_new_node(
        self,
        autodrive_data: AutoDriveData,
        x: float,
        z: float
    ) -> float:
        """Terrain height from the heightmap, otherwise the height of
        the nearest node, otherwise 0."""

        if self.terrain_height_at is not None:
            terrain_height = self.terrain_height_at(
                x,
                z
            )

            if terrain_height is not None:
                return terrain_height

        nearest_node = min(
            autodrive_data.nodes.values(),
            key=lambda node: math.hypot(
                node.x - x,
                node.z - z
            ),
            default=None
        )

        if nearest_node is None:
            return 0.0

        return nearest_node.y
