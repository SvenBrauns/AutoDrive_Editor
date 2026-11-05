from dataclasses import replace

from PySide6.QtCore import QPoint, Signal

from autodrive_editor.editing.commands.add_route import AddRouteCommand
from autodrive_editor.editing.edit_context import EditContext, EditOperation
from autodrive_editor.editing.parallel_lane import (
    Chain,
    ParallelLaneError,
    ParallelLaneOptions,
    parallel_lane,
    selected_chains,
    signed_distance,
)
from autodrive_editor.editing.path_shapes import Point
from autodrive_editor.i18n import tr
from autodrive_editor.model.autodrive_data import NodeData

# The pointer distance is rounded to this, in metres; it is also the smallest distance.
DISTANCE_STEP = 0.5


class ParallelLaneOperation(EditOperation):
    """Creates a lane beside each selected chain of nodes. The pointer sets the side and the
    distance; every chain gets the lane on the same side of its own direction. The new nodes are
    evenly spaced and connected like the chain, in the same or the opposite direction. The ends stay
    open and the new nodes are not selected."""

    # The lanes or the error to show changed.
    preview_changed = Signal()
    # The pointer set a new distance, for the options bar.
    distance_changed = Signal(float)

    def __init__(self, context: EditContext, parent=None):
        super().__init__(context, parent)

        self.options = ParallelLaneOptions()
        # 1: right of the chain's direction, -1: left.
        self.side = 1.0

        self.node_selection.selection_changed.connect(self.preview_changed)
        self.edit_history.data_changed.connect(self.preview_changed)

    @property
    def offset(self) -> float:
        return self.side * self.options.distance

    def set_options(self, options: ParallelLaneOptions):
        self.options = options
        self.preview_changed.emit()

    def pointer_moved(self, view_position: QPoint):
        """Side and distance from the chain nearest to the pointer, rounded to 0.5 m."""

        chains = self._chains_or_none()

        if not chains:
            return

        scene_position = self.view.mapToScene(view_position)
        nodes = self.autodrive_data_provider().nodes
        distance = min(
            (
                signed_distance(
                    [(nodes[i].x, nodes[i].z) for i in chain.node_ids],
                    scene_position.x(),
                    scene_position.y(),
                )
                for chain in chains
            ),
            key=abs,
        )
        rounded = max(DISTANCE_STEP, round(abs(distance) / DISTANCE_STEP) * DISTANCE_STEP)
        side = 1.0 if distance >= 0 else -1.0

        if (rounded, side) == (self.options.distance, self.side):
            return

        self.side = side

        if rounded != self.options.distance:
            self.options = replace(self.options, distance=rounded)
            self.distance_changed.emit(rounded)

        try:
            self._lanes()
        except ParallelLaneError as error:
            self.status_changed.emit(str(error))

        self.preview_changed.emit()

    def preview_lanes(self) -> list[list[Point]]:
        """The (x, z) positions of the new lanes; empty if none can be made."""

        try:
            return [[(x, z) for x, _, z in lane] for _, lane in self._lanes()]
        except ParallelLaneError:
            return []

    def apply(self) -> bool:
        """Creates the lanes as one undo step. Returns True if they were created."""

        autodrive_data = self.autodrive_data_provider()

        if autodrive_data is None or self.edit_history.history_locked:
            return False

        try:
            lanes = self._lanes()
        except ParallelLaneError as error:
            self.status_changed.emit(str(error))
            return False

        if not lanes:
            self.status_changed.emit(tr("Select the nodes of one or more roads first"))
            return False

        next_id = max(autodrive_data.nodes, default=0) + 1
        new_nodes, connections = [], []

        for chain, lane in lanes:
            ids = range(next_id, next_id + len(lane))
            next_id += len(lane)

            for node_id, (x, y, z) in zip(ids, lane, strict=True):
                terrain_y = None if self.terrain_height_at is None else self.terrain_height_at(x, z)
                y = y if terrain_y is None else terrain_y
                new_nodes.append(NodeData(node_id, x, y, z, flag=self.options.flag))

            connections += [(a, b, chain.state) for a, b in zip(ids, ids[1:], strict=False)]

        self.edit_history.push(
            AddRouteCommand(tr("Create parallel lane"), autodrive_data, new_nodes, connections)
        )
        self.status_changed.emit(
            tr(
                "Parallel lanes created: {count}, with {nodes} new nodes",
                count=len(lanes),
                nodes=len(new_nodes),
            )
        )
        self.preview_changed.emit()

        return True

    def _lanes(self) -> list[tuple[Chain, list[tuple[float, float, float]]]]:
        autodrive_data = self.autodrive_data_provider()

        if autodrive_data is None:
            return []

        options = self.options

        return [
            (
                chain,
                parallel_lane(
                    autodrive_data, chain, self.offset, options.spacing, options.opposite
                ),
            )
            for chain in selected_chains(autodrive_data, self._selected_ids(autodrive_data))
        ]

    def _chains_or_none(self) -> list[Chain] | None:
        autodrive_data = self.autodrive_data_provider()

        if autodrive_data is None:
            return None

        try:
            return selected_chains(autodrive_data, self._selected_ids(autodrive_data))
        except ParallelLaneError:
            return None

    def _selected_ids(self, autodrive_data) -> set[int]:
        # The selection may still hold nodes that undo has removed.
        return self.node_selection.selected_node_ids & autodrive_data.nodes.keys()
