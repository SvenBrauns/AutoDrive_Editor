from collections.abc import Callable
from dataclasses import dataclass

from PySide6.QtCore import QObject, QPoint, Signal

from autodrive_editor.editing.commands.create_path import CreatePathCommand
from autodrive_editor.editing.edit_history import EditHistory
from autodrive_editor.editing.path_shapes import (
    PathOptions,
    PathShape,
    Point,
    default_handles,
    shape_polyline,
    spaced_points,
)
from autodrive_editor.i18n import tr
from autodrive_editor.model.autodrive_data import AutoDriveData, NodeData
from autodrive_editor.model.connections import CONNECTION_STATES
from autodrive_editor.selection.selection_coordinator import SelectionCoordinator
from autodrive_editor.terrain.terrain_follower import TerrainHeightProvider
from autodrive_editor.ui.map_view.map_view import MapView

SHAPE_NAMES = {
    PathShape.LINE: tr("Line"),
    PathShape.BEZIER: tr("Bézier curve"),
    PathShape.ARC: tr("Arc"),
}

# Undo texts. Separate from the names, because English writes them in lower case here.
COMMAND_TEXTS = {
    PathShape.LINE: tr("Create line"),
    PathShape.BEZIER: tr("Create Bézier curve"),
    PathShape.ARC: tr("Create arc"),
}

# Clicks closer than this to the start do not count as an end point, in metres.
MIN_PATH_LENGTH = 0.01


@dataclass(frozen=True)
class PathEnd:
    """Start or end of a path: an existing node or a free map point."""

    x: float
    z: float
    node_id: int | None = None


class CreatePathOperation(QObject):
    """Creates straight lines, Bézier curves and circular arcs of evenly
    spaced, connected nodes.

    The first click sets the start, the second the end; both can be an
    existing node or a free point. A line is created right away. Curves
    show handles first, which are dragged until apply() creates the curve.
    The end of each path is the start of the next one.
    """

    status_changed = Signal(str)

    # The start, end, handles or options changed; the preview needs redrawing.
    preview_changed = Signal()

    def __init__(
        self,
        view: MapView,
        selection_coordinator: SelectionCoordinator,
        edit_history: EditHistory,
        autodrive_data_provider: Callable[[], AutoDriveData | None],
        height_for_new_node: Callable[[AutoDriveData, float, float], float],
        terrain_height_at: TerrainHeightProvider | None = None,
        snap_point: Callable[[float, float], tuple[float, float]] | None = None,
        parent=None,
    ):
        super().__init__(parent)

        self.view = view
        self.selection_coordinator = selection_coordinator
        self.edit_history = edit_history
        self.autodrive_data_provider = autodrive_data_provider
        self.height_for_new_node = height_for_new_node
        self.terrain_height_at = terrain_height_at
        self.snap_point = snap_point

        self.shape = PathShape.LINE
        self.options = PathOptions()

        self._start: PathEnd | None = None
        self._end: PathEnd | None = None
        self.handles: list[Point] = []

    @property
    def start(self) -> PathEnd | None:
        return self._current(self._start)

    @property
    def end(self) -> PathEnd | None:
        return self._current(self._end)

    @property
    def is_adjusting(self) -> bool:
        """True while a curve waits for its handles to be dragged."""

        return self.end is not None

    def set_shape(self, shape: PathShape):
        self.reset()
        self.shape = shape

    def set_options(self, options: PathOptions):
        self.options = options
        self.preview_changed.emit()

    def end_at(self, view_position: QPoint) -> PathEnd:
        """The node under the mouse, otherwise the (snapped) map point."""

        node_item = self.selection_coordinator.get_node_item_at(view_position)
        autodrive_data = self.autodrive_data_provider()

        if node_item is not None and autodrive_data is not None:
            node = autodrive_data.get_node(node_item.node_id)

            if node is not None:
                return PathEnd(node.x, node.z, node.node_id)

        scene_position = self.view.mapToScene(view_position)
        x, z = scene_position.x(), scene_position.y()

        if self.snap_point is not None:
            x, z = self.snap_point(x, z)

        return PathEnd(x, z)

    def click(self, view_position: QPoint):
        if self.autodrive_data_provider() is None:
            self.status_changed.emit(tr("Load an AutoDrive XML first"))
            return

        if self.is_adjusting:
            return

        clicked = self.end_at(view_position)
        start = self.start

        if start is None:
            self._start = clicked
            self.status_changed.emit(tr("Start set. Click the end point"))
            self.preview_changed.emit()
            return

        if self._same_point(start, clicked):
            return

        self._end = clicked

        if self.shape == PathShape.LINE:
            self.apply()
            return

        self.handles = default_handles(self.shape, (start.x, start.z), (clicked.x, clicked.z))
        self.status_changed.emit(tr("Drag the handles, Enter creates the curve, Esc cancels"))
        self.preview_changed.emit()

    def move_handle(self, index: int, x: float, z: float):
        self.handles[index] = (x, z)
        self.preview_changed.emit()

    def preview_points(self, mouse_end: PathEnd | None = None) -> list[Point]:
        """Positions of all nodes of the pending path, including start and end.
        Before the end is set, the mouse position is used as end of a line."""

        start, end = self.start, self.end

        if start is None:
            return []

        if end is None:
            if mouse_end is None or self._same_point(start, mouse_end):
                return []

            polyline = [(start.x, start.z), (mouse_end.x, mouse_end.z)]

        else:
            polyline = shape_polyline(self.shape, (start.x, start.z), (end.x, end.z), self.handles)

        return spaced_points(polyline, self.options.spacing)

    def apply(self) -> bool:
        """Creates the pending path. Returns True if it was created."""

        autodrive_data = self.autodrive_data_provider()
        start, end = self.start, self.end

        if autodrive_data is None or start is None or end is None:
            return False

        if self.edit_history.history_locked:
            return False

        points = self.preview_points()
        next_id = max(autodrive_data.nodes, default=0) + 1
        new_nodes = []

        def node_for(path_end: PathEnd) -> NodeData:
            """The existing node, or a new one at the free point."""

            nonlocal next_id

            if path_end.node_id is not None:
                return autodrive_data.nodes[path_end.node_id]

            x, z = path_end.x, path_end.z
            y = self.height_for_new_node(autodrive_data, x, z)
            node = NodeData(next_id, x, y, z, flag=self.options.flag)
            new_nodes.append(node)
            next_id += 1

            return node

        start_node, end_node = node_for(start), node_for(end)
        start_id, end_id = start_node.node_id, end_node.node_id
        start_y, end_y = start_node.y, end_node.y

        inner_ids = []

        for index, (x, z) in enumerate(points[1:-1], start=1):
            y = self._terrain_height(x, z)

            if y is None:
                y = start_y + (end_y - start_y) * index / (len(points) - 1)

            new_nodes.append(NodeData(next_id, x, y, z, flag=self.options.flag))
            inner_ids.append(next_id)
            next_id += 1

        name = SHAPE_NAMES[self.shape]

        self.edit_history.push(
            CreatePathCommand(
                COMMAND_TEXTS[self.shape],
                autodrive_data,
                [start_id, *inner_ids, end_id],
                new_nodes,
                CONNECTION_STATES[self.options.connection_type],
            )
        )

        self.status_changed.emit(
            tr(
                "{shape} with {count} new nodes created. Click the next end point",
                shape=name,
                count=len(new_nodes),
            )
        )

        # The end is the start of the next path.
        self._start = PathEnd(end.x, end.z, end_id)
        self._end = None
        self.handles = []
        self.preview_changed.emit()

        return True

    def cancel(self) -> bool:
        """Esc: drops the pending curve, otherwise the start. Returns True if
        something was dropped."""

        if self.is_adjusting:
            self._end = None
            self.handles = []
            self.status_changed.emit(tr("Curve discarded. Click the end point"))

        elif self.start is not None:
            self._start = None
            self.status_changed.emit(tr("Path finished"))

        else:
            return False

        self.preview_changed.emit()

        return True

    def reset(self):
        self._start = None
        self._end = None
        self.handles = []
        self.preview_changed.emit()

    def _current(self, path_end: PathEnd | None) -> PathEnd | None:
        """The path end with the current node position. None if its node no
        longer exists, e.g. after undo."""

        if path_end is None or path_end.node_id is None:
            return path_end

        autodrive_data = self.autodrive_data_provider()
        node = None if autodrive_data is None else autodrive_data.get_node(path_end.node_id)

        if node is None:
            return None

        return PathEnd(node.x, node.z, node.node_id)

    def _terrain_height(self, x: float, z: float) -> float | None:
        if self.terrain_height_at is None:
            return None

        return self.terrain_height_at(x, z)

    @staticmethod
    def _same_point(a: PathEnd, b: PathEnd) -> bool:
        if a.node_id is not None and a.node_id == b.node_id:
            return True

        return abs(a.x - b.x) + abs(a.z - b.z) < MIN_PATH_LENGTH
