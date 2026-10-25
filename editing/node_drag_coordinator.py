import itertools

from collections.abc import Callable

from PySide6.QtCore import (
    QObject,
    QPoint,
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
from selection.selection_coordinator import (
    SelectionCoordinator
)
from ui.map_view import MapView


class NodeDragCoordinator(QObject):
    """Moves nodes by left dragging with the "Verschieben" tool.

    Dragging a selected node moves the whole selection. Dragging an
    unselected node moves only that node. The selection itself is
    never changed. Every mouse move pushes a MoveNodesCommand with the
    same merge key, so the whole drag is a single undo step.
    """

    status_changed = Signal(
        str
    )

    def __init__(
        self,
        view: MapView,
        selection_coordinator: SelectionCoordinator,
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

        self.view = view
        self.selection_coordinator = selection_coordinator
        self.selection_manager = selection_manager
        self.edit_coordinator = edit_coordinator
        self.autodrive_data_provider = (
            autodrive_data_provider
        )

        self._merge_keys = itertools.count(
            1
        )

        self._reset_state()

    @property
    def is_dragging(self) -> bool:
        return self._moved

    def begin_drag(
        self,
        view_position: QPoint
    ) -> bool:
        """Prepares a drag of the node at the given view position.
        Returns False if there is no node to drag there."""

        self._end_drag()

        autodrive_data = self.autodrive_data_provider()

        if autodrive_data is None:
            return False

        node_item = (
            self.selection_coordinator
            .get_node_item_at(
                view_position
            )
        )

        if node_item is None:
            return False

        pressed_node_id = node_item.node_id

        selected_node_ids = (
            self.selection_manager.selected_node_ids
        )

        if pressed_node_id in selected_node_ids:
            moving_node_ids = selected_node_ids

        else:
            moving_node_ids = {
                pressed_node_id
            }

        self._autodrive_data = autodrive_data

        self._press_scene_position = QPointF(
            self.view.mapToScene(
                view_position
            )
        )

        self._start_positions = self._read_positions(
            moving_node_ids
        )

        self._merge_key = next(
            self._merge_keys
        )

        return True

    def update_drag(
        self,
        view_position: QPoint
    ):
        if not self._start_positions:
            return

        if not self._moved:
            self._begin_move()

        scene_position = self.view.mapToScene(
            view_position
        )

        delta_x = (
            scene_position.x()
            - self._press_scene_position.x()
        )

        delta_z = (
            scene_position.y()
            - self._press_scene_position.y()
        )

        self._push_positions(
            {
                node_id: (
                    x + delta_x,
                    y,
                    z + delta_z
                )
                for node_id, (x, y, z)
                in self._start_positions.items()
            }
        )

    def finish_drag(self):
        if self._moved:
            moved_count = len(
                self._start_positions
            )

            self.status_changed.emit(
                "Node verschoben"
                if moved_count == 1
                else f"{moved_count} Nodes verschoben"
            )

        self._end_drag()

    def cancel_drag(self):
        if self._moved:
            # Moving back to the start merges into the drag's command,
            # which then becomes obsolete and leaves the undo history.
            self._push_positions(
                dict(
                    self._start_positions
                )
            )

            self.status_changed.emit(
                "Verschieben abgebrochen"
            )

        self._end_drag()

    def _begin_move(self):
        self._moved = True

        self.edit_coordinator.set_history_locked(
            True
        )

    def _push_positions(
        self,
        target_positions: dict[int, NodePosition]
    ):
        self.edit_coordinator.push(
            MoveNodesCommand(
                autodrive_data=self._autodrive_data,
                old_positions=self._read_positions(
                    target_positions
                ),
                new_positions=target_positions,
                merge_key=self._merge_key
            )
        )

    def _read_positions(
        self,
        node_ids
    ) -> dict[int, NodePosition]:
        return {
            node_id: (
                node.x,
                node.y,
                node.z
            )
            for node_id in node_ids
            if (
                node := self._autodrive_data.get_node(
                    node_id
                )
            ) is not None
        }

    def _end_drag(self):
        if self._moved:
            self.edit_coordinator.set_history_locked(
                False
            )

        self._reset_state()

    def _reset_state(self):
        self._autodrive_data: AutoDriveData | None = None
        self._press_scene_position = QPointF()
        self._start_positions: dict[int, NodePosition] = {}
        self._merge_key = None
        self._moved = False
