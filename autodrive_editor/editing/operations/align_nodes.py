from collections.abc import Callable

from PySide6.QtCore import QObject, QPoint, QPointF, Signal

from autodrive_editor.editing.commands.move_nodes import MoveNodesCommand, NodePosition
from autodrive_editor.editing.edit_history import EditHistory
from autodrive_editor.i18n import tr
from autodrive_editor.model.autodrive_data import AutoDriveData, NodeData
from autodrive_editor.selection.node_selection import NodeSelection
from autodrive_editor.selection.selection_coordinator import SelectionCoordinator
from autodrive_editor.terrain.terrain_follower import TerrainFollower, TerrainHeightProvider
from autodrive_editor.ui.map_view.map_view import MapView


class AlignNodesOperation(QObject):
    """Aligns the selected nodes to a clicked reference node.

    "Horizontal" and "vertical" refer to the screen axes of the current
    view, so they also work when the map is rotated.
    """

    status_changed = Signal(str)

    NO_SELECTION_TEXT = tr("First select the nodes to align")

    def __init__(
        self,
        view: MapView,
        selection_coordinator: SelectionCoordinator,
        node_selection: NodeSelection,
        edit_history: EditHistory,
        autodrive_data_provider: Callable[[], AutoDriveData | None],
        terrain_height_at: TerrainHeightProvider | None = None,
        parent=None,
    ):
        super().__init__(parent)

        self.view = view
        self.selection_coordinator = selection_coordinator
        self.node_selection = node_selection
        self.edit_history = edit_history
        self.autodrive_data_provider = autodrive_data_provider
        self.terrain_height_at = terrain_height_at

    def align_horizontal_at(self, view_position: QPoint) -> bool:
        return self._align_on_screen_axis(view_position, keep_screen_x=True)

    def align_vertical_at(self, view_position: QPoint) -> bool:
        return self._align_on_screen_axis(view_position, keep_screen_x=False)

    def align_height_at(self, view_position: QPoint) -> bool:
        """The selected nodes get the reference node's height."""

        target = self._reference_and_selection(view_position)

        if target is None:
            return False

        autodrive_data, reference, nodes = target

        positions = {node.node_id: (node.x, reference.y, node.z) for node in nodes}

        return self._push(autodrive_data, nodes, positions, tr("Match height"))

    def height_from_terrain_at(self, view_position: QPoint) -> bool:
        """Each selected node gets the terrain height at its position."""

        target = self._reference_and_selection(view_position)

        if target is None:
            return False

        autodrive_data, _, nodes = target

        heights = {
            node.node_id: self.terrain_height_at(node.x, node.z) if self.terrain_height_at else None
            for node in nodes
        }

        if all(height is None for height in heights.values()):
            self.status_changed.emit(tr("No heightmap loaded"))
            return False

        positions = {
            node.node_id: (
                node.x,
                node.y if heights[node.node_id] is None else heights[node.node_id],
                node.z,
            )
            for node in nodes
        }

        return self._push(autodrive_data, nodes, positions, tr("Height from heightmap"))

    def _align_on_screen_axis(self, view_position: QPoint, keep_screen_x: bool) -> bool:
        target = self._reference_and_selection(view_position)

        if target is None:
            return False

        autodrive_data, reference, nodes = target

        # The view transform maps map coordinates to screen axes, including
        # rotation. Only the position along one screen axis changes.
        to_screen = self.view.transform()
        to_map, _ = to_screen.inverted()
        reference_on_screen = to_screen.map(QPointF(reference.x, reference.z))

        follower = TerrainFollower(self.terrain_height_at)
        follower.begin({node.node_id: (node.x, node.y, node.z) for node in nodes})

        positions = {}

        for node in nodes:
            on_screen = to_screen.map(QPointF(node.x, node.z))

            if keep_screen_x:
                on_screen.setY(reference_on_screen.y())
            else:
                on_screen.setX(reference_on_screen.x())

            on_map = to_map.map(on_screen)
            new_x, new_z = on_map.x(), on_map.y()
            start = (node.x, node.y, node.z)

            positions[node.node_id] = (
                new_x,
                follower.height_at(node.node_id, start, new_x, new_z),
                new_z,
            )

        text = tr("Align horizontally") if keep_screen_x else tr("Align vertically")

        return self._push(autodrive_data, nodes, positions, text)

    def _reference_and_selection(
        self, view_position: QPoint
    ) -> tuple[AutoDriveData, NodeData, list[NodeData]] | None:
        autodrive_data = self.autodrive_data_provider()

        if autodrive_data is None or self.edit_history.history_locked:
            return None

        clicked_node = self.selection_coordinator.get_node_at(view_position)

        if clicked_node is None:
            return None

        reference = autodrive_data.nodes[clicked_node.node_id]

        nodes = [
            autodrive_data.nodes[node_id]
            for node_id in sorted(self.node_selection.selected_node_ids)
            if node_id in autodrive_data.nodes and node_id != reference.node_id
        ]

        if not nodes:
            self.status_changed.emit(self.NO_SELECTION_TEXT)
            return None

        return autodrive_data, reference, nodes

    def _push(
        self,
        autodrive_data: AutoDriveData,
        nodes: list[NodeData],
        new_positions: dict[int, NodePosition],
        text: str,
    ) -> bool:
        old_positions = {node.node_id: (node.x, node.y, node.z) for node in nodes}
        command = MoveNodesCommand(autodrive_data, old_positions, new_positions, text=text)

        if command.isObsolete():
            self.status_changed.emit(tr("The nodes are already aligned"))
            return False

        self.edit_history.push(command)

        count = len(nodes)
        self.status_changed.emit(
            tr("{text}: 1 node", text=text)
            if count == 1
            else tr("{text}: {count} nodes", text=text, count=count)
        )

        return True
