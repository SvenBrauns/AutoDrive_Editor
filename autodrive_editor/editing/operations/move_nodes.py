import itertools
import math

from PySide6.QtCore import QPoint, QPointF

from autodrive_editor.editing.commands.move_nodes import MoveNodesCommand, NodePosition
from autodrive_editor.editing.edit_context import EditContext, EditOperation
from autodrive_editor.i18n import tr
from autodrive_editor.model.autodrive_data import AutoDriveData
from autodrive_editor.terrain.terrain_follower import TerrainFollower


class MoveNodesOperation(EditOperation):
    """Moves nodes by left dragging with the "Verschieben" tool.

    Dragging a selected node moves the whole selection. Dragging an
    unselected node moves only that node. The selection itself is
    never changed. Every mouse move pushes a MoveNodesCommand with the
    same merge key, so the whole drag is a single undo step.
    """

    def __init__(self, context: EditContext, parent=None):
        super().__init__(context, parent)

        self.terrain_follower = TerrainFollower(context.terrain_height_at)

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

        clicked_node = self.selection_coordinator.get_node_at(view_position)

        if clicked_node is None:
            return False

        pressed_node_id = clicked_node.node_id

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

    def update_drag(self, view_position: QPoint, axis_lock: bool = False):
        """Moves the nodes with the mouse. With axis_lock, they move only
        along the grid axis the mouse has moved further along."""

        if not self._start_positions:
            return

        if not self._moved:
            self._begin_move()

        scene_position = self.view.mapToScene(view_position)

        delta_x = scene_position.x() - self._press_scene_position.x()

        delta_z = scene_position.y() - self._press_scene_position.y()

        axis = self._dominant_grid_axis(delta_x, delta_z) if axis_lock else None

        if self.snap_point is not None:
            grabbed_start = self._start_positions[self._grabbed_node_id]
            snapped_x, snapped_z = self.snap_point(
                grabbed_start[0] + delta_x, grabbed_start[2] + delta_z
            )
            delta_x = snapped_x - grabbed_start[0]
            delta_z = snapped_z - grabbed_start[2]

        if axis is not None:
            along = delta_x * axis[0] + delta_z * axis[1]
            delta_x, delta_z = along * axis[0], along * axis[1]

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
                tr("Node moved")
                if moved_count == 1
                else tr("{count} nodes moved", count=moved_count)
            )

        self._end_drag()

    def cancel_drag(self):
        if self._moved:
            # Moving back to the start merges into the drag's command,
            # which then becomes obsolete and leaves the undo history.
            self._push_positions(dict(self._start_positions))

            self.status_changed.emit(tr("Moving cancelled"))

        self._end_drag()

    def _dominant_grid_axis(self, delta_x: float, delta_z: float) -> tuple[float, float]:
        """Unit vector of the grid axis (X or Z, rotated with the grid) that
        the movement follows more."""

        rotation = math.radians(self.grid_rotation() if self.grid_rotation else 0.0)
        x_axis = (math.cos(rotation), math.sin(rotation))
        z_axis = (-math.sin(rotation), math.cos(rotation))

        along_x = delta_x * x_axis[0] + delta_z * x_axis[1]
        along_z = delta_x * z_axis[0] + delta_z * z_axis[1]

        return x_axis if abs(along_x) >= abs(along_z) else z_axis

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
