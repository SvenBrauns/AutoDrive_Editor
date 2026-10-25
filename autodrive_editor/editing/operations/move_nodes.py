import itertools
from collections.abc import Callable

from PySide6.QtCore import QObject, QPoint, QPointF, Signal

from autodrive_editor.editing.commands.move_nodes import MoveNodesCommand, NodePosition
from autodrive_editor.editing.edit_history import EditHistory
from autodrive_editor.model.autodrive_data import AutoDriveData
from autodrive_editor.selection.node_selection import NodeSelection
from autodrive_editor.selection.selection_coordinator import SelectionCoordinator
from autodrive_editor.terrain.terrain_follower import TerrainFollower, TerrainHeightProvider
from autodrive_editor.ui.map_view.map_view import MapView


class MoveNodesOperation(QObject):
    """Moves nodes by left dragging with the "Verschieben" tool.

    Dragging a selected node moves the whole selection. Dragging an
    unselected node moves only that node. The selection itself is
    never changed. Every mouse move pushes a MoveNodesCommand with the
    same merge key, so the whole drag is a single undo step.
    """

    status_changed = Signal(str)

    def __init__(
        self,
        view: MapView,
        selection_coordinator: SelectionCoordinator,
        node_selection: NodeSelection,
        edit_history: EditHistory,
        autodrive_data_provider: Callable[[], AutoDriveData | None],
        terrain_height_at: TerrainHeightProvider | None = None,
        snap_point: Callable[[float, float], tuple[float, float]] | None = None,
        parent=None,
    ):
        super().__init__(parent)

        self.terrain_follower = TerrainFollower(terrain_height_at)

        # Grid snapping; the grabbed node snaps, the others keep their offset.
        self.snap_point = snap_point

        self.view = view
        self.selection_coordinator = selection_coordinator
        self.node_selection = node_selection
        self.edit_history = edit_history
        self.autodrive_data_provider = autodrive_data_provider

        self._merge_keys = itertools.count(1)

        self._reset_state()

    @property
    def is_dragging(self) -> bool:
        return self._moved

    def begin_drag(self, view_position: QPoint) -> bool:
        """Prepares a drag of the node at the given view position.
        Returns False if there is no node to drag there."""

        self._end_drag()

        autodrive_data = self.autodrive_data_provider()

        if autodrive_data is None:
            return False

        node_item = self.selection_coordinator.get_node_item_at(view_position)

        if node_item is None:
            return False

        pressed_node_id = node_item.node_id

        selected_node_ids = self.node_selection.selected_node_ids

        if pressed_node_id in selected_node_ids:
            moving_node_ids = selected_node_ids

        else:
            moving_node_ids = {pressed_node_id}

        self._autodrive_data = autodrive_data

        self._grabbed_node_id = pressed_node_id

        self._press_scene_position = QPointF(self.view.mapToScene(view_position))

        self._start_positions = self._read_positions(moving_node_ids)

        self.terrain_follower.begin(self._start_positions)

        self._merge_key = next(self._merge_keys)

        return True

    def update_drag(self, view_position: QPoint):
        if not self._start_positions:
            return

        if not self._moved:
            self._begin_move()

        scene_position = self.view.mapToScene(view_position)

        delta_x = scene_position.x() - self._press_scene_position.x()

        delta_z = scene_position.y() - self._press_scene_position.y()

        if self.snap_point is not None:
            grabbed_start = self._start_positions[self._grabbed_node_id]
            snapped_x, snapped_z = self.snap_point(
                grabbed_start[0] + delta_x, grabbed_start[2] + delta_z
            )
            delta_x = snapped_x - grabbed_start[0]
            delta_z = snapped_z - grabbed_start[2]

        target_positions = {}

        for node_id, start in self._start_positions.items():
            new_x = start[0] + delta_x
            new_z = start[2] + delta_z

            target_positions[node_id] = (
                new_x,
                self.terrain_follower.height_at(node_id, start, new_x, new_z),
                new_z,
            )

        self._push_positions(target_positions)

    def finish_drag(self):
        if self._moved:
            moved_count = len(self._start_positions)

            self.status_changed.emit(
                "Node verschoben" if moved_count == 1 else f"{moved_count} Nodes verschoben"
            )

        self._end_drag()

    def cancel_drag(self):
        if self._moved:
            # Moving back to the start merges into the drag's command,
            # which then becomes obsolete and leaves the undo history.
            self._push_positions(dict(self._start_positions))

            self.status_changed.emit("Verschieben abgebrochen")

        self._end_drag()

    def _begin_move(self):
        self._moved = True

        self.edit_history.set_history_locked(True)

    def _push_positions(self, target_positions: dict[int, NodePosition]):
        self.edit_history.push(
            MoveNodesCommand(
                autodrive_data=self._autodrive_data,
                old_positions=self._read_positions(target_positions),
                new_positions=target_positions,
                merge_key=self._merge_key,
            )
        )

    def _read_positions(self, node_ids) -> dict[int, NodePosition]:
        return {
            node_id: (node.x, node.y, node.z)
            for node_id in node_ids
            if (node := self._autodrive_data.get_node(node_id)) is not None
        }

    def _end_drag(self):
        if self._moved:
            self.edit_history.set_history_locked(False)

        self._reset_state()

    def _reset_state(self):
        self._autodrive_data: AutoDriveData | None = None
        self._grabbed_node_id: int | None = None
        self._press_scene_position = QPointF()
        self._start_positions: dict[int, NodePosition] = {}
        self._merge_key = None
        self._moved = False
