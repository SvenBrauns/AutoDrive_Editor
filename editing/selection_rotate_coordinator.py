import itertools
import math

from collections.abc import Callable

from PySide6.QtCore import (
    QObject,
    QPointF,
    Signal
)

from autodrive.models import AutoDriveData
from editing.edit_coordinator import EditCoordinator
from editing.move_nodes_command import (
    MoveNodesCommand,
    NodePosition
)
from selection.node_selection_manager import (
    NodeSelectionManager
)


class SelectionRotateCoordinator(QObject):
    """Rotates the selected nodes around their average center.

    Every mouse move pushes a MoveNodesCommand with the same merge key,
    so a whole rotation is a single undo step.
    """

    MIN_NODE_COUNT = 2
    SNAP_ANGLE_DEGREES = 15.0

    status_changed = Signal(
        str
    )

    # Emitted when the selection or node positions change, so the
    # rotation ring can follow.
    target_changed = Signal()

    def __init__(
        self,
        selection_manager: NodeSelectionManager,
        edit_coordinator: EditCoordinator,
        autodrive_data_provider: Callable[
            [],
            AutoDriveData | None
        ],
        parent=None
    ):
        super().__init__(
            parent
        )

        self.selection_manager = selection_manager
        self.edit_coordinator = edit_coordinator
        self.autodrive_data_provider = (
            autodrive_data_provider
        )

        self._merge_keys = itertools.count(
            1
        )

        self._reset_state()

        selection_manager.selection_changed.connect(
            lambda node_ids, primary_node_id:
            self.target_changed.emit()
        )

        edit_coordinator.data_changed.connect(
            lambda data_change: self.target_changed.emit()
        )

    @property
    def is_rotating(self) -> bool:
        return bool(
            self._start_positions
        )

    def rotation_target(
        self
    ) -> tuple[QPointF, float] | None:
        """Returns the average center of the selected nodes and the
        largest distance of a selected node from it, or None if fewer
        than two nodes are selected."""

        autodrive_data = self.autodrive_data_provider()

        if autodrive_data is None:
            return None

        nodes = [
            autodrive_data.nodes[node_id]
            for node_id in self.selection_manager.selected_node_ids
            if node_id in autodrive_data.nodes
        ]

        if len(nodes) < self.MIN_NODE_COUNT:
            return None

        center_x = sum(node.x for node in nodes) / len(nodes)
        center_z = sum(node.z for node in nodes) / len(nodes)

        radius = max(
            math.hypot(
                node.x - center_x,
                node.z - center_z
            )
            for node in nodes
        )

        return (
            QPointF(center_x, center_z),
            radius
        )

    def begin_rotation(
        self,
        scene_position: QPointF
    ) -> bool:
        """Starts a rotation grabbed at the given scene position.
        Returns False if the selection cannot be rotated."""

        self._end_rotation()

        if self.edit_coordinator.history_locked:
            return False

        target = self.rotation_target()

        if target is None:
            return False

        center, _ = target

        autodrive_data = self.autodrive_data_provider()

        self._autodrive_data = autodrive_data
        self._center = center

        self._start_angle = self._angle_to(
            scene_position
        )

        self._start_positions = {
            node_id: (
                node.x,
                node.y,
                node.z
            )
            for node_id in self.selection_manager.selected_node_ids
            if (
                node := autodrive_data.get_node(
                    node_id
                )
            ) is not None
        }

        self._merge_key = next(
            self._merge_keys
        )

        return True

    def update_rotation(
        self,
        scene_position: QPointF,
        snap: bool = False
    ) -> float | None:
        """Rotates the selection so the grabbed point follows the
        mouse. Returns the rotation angle in degrees."""

        if not self.is_rotating:
            return None

        if not self._history_locked:
            self.edit_coordinator.set_history_locked(
                True
            )

            self._history_locked = True

        angle = math.degrees(
            self._angle_to(scene_position)
            - self._start_angle
        )

        # Shows -180..180 instead of e.g. 350 for small left turns.
        angle = (angle + 180.0) % 360.0 - 180.0

        if snap:
            angle = (
                round(angle / self.SNAP_ANGLE_DEGREES)
                * self.SNAP_ANGLE_DEGREES
            )

        self._angle = angle

        self._push_positions(
            self._rotated_positions(
                angle
            )
        )

        self.status_changed.emit(
            f"Rotation: {angle:.1f}°"
        )

        return angle

    def finish_rotation(self):
        if self.is_rotating and self._history_locked:
            self.status_changed.emit(
                f"{len(self._start_positions)} Nodes "
                f"um {self._angle:.1f}° rotiert"
            )

        self._end_rotation()

    def cancel_rotation(self):
        if self.is_rotating and self._history_locked:
            # Rotating back to the start merges into the rotation's
            # command, which then becomes obsolete and disappears.
            self._push_positions(
                dict(
                    self._start_positions
                )
            )

            self.status_changed.emit(
                "Rotation abgebrochen"
            )

        self._end_rotation()

    def _rotated_positions(
        self,
        angle_degrees: float
    ) -> dict[int, NodePosition]:
        angle = math.radians(
            angle_degrees
        )

        cos_angle = math.cos(angle)
        sin_angle = math.sin(angle)

        center_x = self._center.x()
        center_z = self._center.y()

        rotated = {}

        for node_id, (x, y, z) in self._start_positions.items():
            offset_x = x - center_x
            offset_z = z - center_z

            rotated[node_id] = (
                center_x
                + offset_x * cos_angle
                - offset_z * sin_angle,
                y,
                center_z
                + offset_x * sin_angle
                + offset_z * cos_angle
            )

        return rotated

    def _push_positions(
        self,
        target_positions: dict[int, NodePosition]
    ):
        nodes = self._autodrive_data.nodes

        self.edit_coordinator.push(
            MoveNodesCommand(
                autodrive_data=self._autodrive_data,
                old_positions={
                    node_id: (
                        nodes[node_id].x,
                        nodes[node_id].y,
                        nodes[node_id].z
                    )
                    for node_id in target_positions
                },
                new_positions=target_positions,
                merge_key=("rotate", self._merge_key),
                text=f"{len(target_positions)} Nodes rotieren"
            )
        )

    def _angle_to(
        self,
        scene_position: QPointF
    ) -> float:
        return math.atan2(
            scene_position.y() - self._center.y(),
            scene_position.x() - self._center.x()
        )

    def _end_rotation(self):
        if self._history_locked:
            self.edit_coordinator.set_history_locked(
                False
            )

        self._reset_state()

    def _reset_state(self):
        self._autodrive_data: AutoDriveData | None = None
        self._center = QPointF()
        self._start_angle = 0.0
        self._angle = 0.0
        self._start_positions: dict[int, NodePosition] = {}
        self._merge_key = None
        self._history_locked = False
