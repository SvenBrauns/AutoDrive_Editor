import math
import threading
from collections.abc import Callable
from dataclasses import dataclass

from PySide6.QtCore import Signal

from autodrive_editor.editing.dubins import Pose
from autodrive_editor.editing.edit_context import EditContext, EditOperation
from autodrive_editor.editing.junction import (
    BOTH,
    LANE_GAP,
    YARD_RADIUS,
    JunctionPlan,
    RoadLane,
    Stem,
    junction_command,
    junction_distance,
    plan_junction,
    road_lanes,
    uses_two_lanes,
)
from autodrive_editor.editing.route_finder import RouteFinder, Vehicle
from autodrive_editor.file_io.navigation_costmap import NavigationCostmap
from autodrive_editor.i18n import tr
from autodrive_editor.model.autodrive_data import AutoDriveData


@dataclass(frozen=True)
class JunctionPreview:
    plan: JunctionPlan
    # Where the curves meet, heading into the yard, and the stem beyond it.
    junction: Pose
    stem_length: float
    # Gap between the lanes of a two-lane stem, 0 for a two-way stem.
    gap: float = 0.0


class JunctionOperation(EditOperation):
    """Junction task: pressing on a road connection and dragging away from the road previews a
    junction (curves in and out at the yard radius, a stem to the drag end: two-way or two one-way
    lanes, see Stem); release adds
    it to the plan as one undo step. Curves that do not fit as drawn are searched with the route
    finder in a background thread first."""

    preview_changed = Signal()
    # A search started or ended.
    searching_changed = Signal(bool)
    # From the search thread: the finished plan, or None if cancelled.
    _search_done = Signal(object)

    def __init__(
        self,
        context: EditContext,
        costmap_provider: Callable[[], NavigationCostmap | None],
        vehicle_provider: Callable[[], Vehicle],
        spacing_provider: Callable[[], float],
        height_for_new_node: Callable[[AutoDriveData, float, float], float],
        stem_provider: Callable[[], tuple[Stem, float]] = lambda: (Stem.AUTO, LANE_GAP),
        parent=None,
    ):
        super().__init__(context, parent)

        self.costmap_provider = costmap_provider
        self.vehicle_provider = vehicle_provider
        self.spacing_provider = spacing_provider
        self.height_for_new_node = height_for_new_node
        self.stem_provider = stem_provider

        self.preview: JunctionPreview | None = None
        self._lanes: list[RoadLane] = []
        self._connection: tuple[int, int] | None = None
        self._foot: tuple[float, float] | None = None
        self._running: dict | None = None
        self._search_done.connect(self._finish)

    @property
    def is_searching(self) -> bool:
        return self._running is not None

    def start(self, source_id: int, target_id: int, x: float, z: float) -> bool:
        """Starts a junction on the road through the connection, at the point closest to
        (x, z)."""

        autodrive_data = self.autodrive_data_provider()

        if autodrive_data is None or self.edit_history.history_locked or self.is_searching:
            return False

        source, target = autodrive_data.nodes[source_id], autodrive_data.nodes[target_id]
        dx, dz = target.x - source.x, target.z - source.z
        fraction = ((x - source.x) * dx + (z - source.z) * dz) / (dx * dx + dz * dz or 1.0)
        fraction = min(max(fraction, 0.0), 1.0)

        self._connection = (source_id, target_id)
        self._foot = (source.x + fraction * dx, source.z + fraction * dz)
        self._lanes = road_lanes(autodrive_data, source_id, target_id)
        self.preview = None

        return True

    def drag_to(self, x: float, z: float):
        """Previews the junction with the stem towards (x, z)."""

        if self._foot is None:
            return

        foot_x, foot_z = self._foot
        length = math.hypot(x - foot_x, z - foot_z)

        if length < 1e-6:
            return

        heading = math.atan2(z - foot_z, x - foot_x)
        stem, gap = self.stem_provider()
        gap = gap if uses_two_lanes(stem, self._lanes) else 0.0
        distance = junction_distance(self._lanes, self._foot, heading, YARD_RADIUS, gap)
        junction = (
            foot_x + distance * math.cos(heading),
            foot_z + distance * math.sin(heading),
            heading,
        )
        plan = self._plan(junction, gap)
        self.preview = JunctionPreview(plan, junction, max(0.0, length - distance), gap)
        self.preview_changed.emit()

    def finish(self) -> bool:
        """Adds the previewed junction to the plan, once the curves that do not fit as drawn
        have been searched."""

        preview = self.preview

        if preview is None or self._foot is None:
            self.cancel()
            return False

        if not self.edit_history.is_planning:
            self.status_changed.emit(tr("Junctions are added in planning mode"))
            self.cancel()
            return False

        if not preview.plan.missing:
            return self._add(preview)

        costmap = self.costmap_provider()

        if costmap is None:
            return self._add(preview)

        finder = RouteFinder(costmap, self.vehicle_provider())
        cancelled = threading.Event()
        self._running = {"cancelled": cancelled, "preview": preview}

        def search():
            def find_route(request):
                return None if cancelled.is_set() else finder.find(request, cancelled.is_set)

            plan = self._plan(preview.junction, preview.gap, find_route)

            try:
                self._search_done.emit(None if cancelled.is_set() else plan)
            except RuntimeError:
                # The window was closed during the search.
                pass

        threading.Thread(target=search, daemon=True).start()
        self.searching_changed.emit(True)
        self.status_changed.emit(tr("Searching the curves that do not fit…"))

        return True

    def cancel(self) -> bool:
        had_something = self.preview is not None or self._running is not None

        if self._running is not None:
            self._running["cancelled"].set()

        self._foot = None
        self._lanes = []
        self.preview = None
        self.preview_changed.emit()

        return had_something

    def _plan(self, junction: Pose, gap: float, find_route=None) -> JunctionPlan:
        autodrive_data = self.autodrive_data_provider()

        return plan_junction(
            self._lanes,
            junction,
            BOTH,
            YARD_RADIUS,
            self.costmap_provider(),
            self.vehicle_provider(),
            frozenset(autodrive_data.markers),
            find_route,
            gap,
        )

    def _finish(self, plan: JunctionPlan | None):
        running, self._running = self._running, None
        self.searching_changed.emit(False)

        if plan is None or running is None or running["cancelled"].is_set():
            return

        preview = running["preview"]
        self._add(JunctionPreview(plan, preview.junction, preview.stem_length, preview.gap))

    def _add(self, preview: JunctionPreview) -> bool:
        autodrive_data = self.autodrive_data_provider()
        nodes = autodrive_data.nodes if autodrive_data is not None else {}
        lane_ids = {node_id for curve in preview.plan.curves for node_id in curve.lane.node_ids}

        if not preview.plan.curves or not lane_ids <= set(nodes):
            self.status_changed.emit(tr("No curve of the junction fits here"))
            self.cancel()
            return False

        command = junction_command(
            autodrive_data,
            preview.plan,
            preview.junction,
            self.spacing_provider(),
            self.height_for_new_node,
            stem_length=preview.stem_length,
            gap=preview.gap,
        )
        self.cancel()
        self.edit_history.push(command)

        if preview.plan.missing:
            self.status_changed.emit(
                tr("Junction added; missing: {missing}", missing=", ".join(preview.plan.missing))
            )
        else:
            self.status_changed.emit(tr("Junction added"))

        return True
