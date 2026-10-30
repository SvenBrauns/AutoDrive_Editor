import logging
import math
import threading
from collections.abc import Callable
from dataclasses import dataclass
from itertools import pairwise

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
    foot_on_lane,
    is_on_two_way_road,
    junction_command,
    junction_distance,
    plan_junction,
    road_lanes,
    roads_across,
    stem_poses,
    uses_two_lanes,
)
from autodrive_editor.editing.route_finder import RouteFinder, Vehicle
from autodrive_editor.file_io.navigation_costmap import NavigationCostmap
from autodrive_editor.i18n import tr
from autodrive_editor.model.autodrive_data import AutoDriveData

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class JunctionPreview:
    plan: JunctionPlan
    # Where the curves meet, heading into the yard.
    junction: Pose
    # The stem's centre line from the junction to its tip (see stem_poses).
    stem: tuple[Pose, ...]
    # Gap between the lanes of a two-lane stem, 0 for a two-way stem.
    gap: float = 0.0
    # The existing node the stem's tip joins, if any.
    tip_id: int | None = None

    @property
    def stem_length(self) -> float:
        return sum(math.dist(a[:2], b[:2]) for a, b in pairwise(self.stem))


class JunctionOperation(EditOperation):
    """Junction task in two steps. Step 1: pressing on a road connection and dragging previews
    a junction (curves in and out at the yard radius, a stem of two-way or two one-way lanes,
    see Stem) at the road point closest to the mouse, the stem square to the road and as long
    as the mouse is far from it. Step 2, after release: dragging the stem's tip bends the stem;
    dropping it on a node joins it. finish adds the junction to the plan as one undo step;
    curves that do not fit as drawn are searched with the route finder in a background thread
    first. Where turn curves of a road on the far side meet the road, straight lanes lead
    across to it (see roads_across)."""

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
        self._across: list = []
        self._foot: tuple[float, float] | None = None
        self._bending = False
        self._running: dict | None = None
        self._search_done.connect(self._finish)

    @property
    def is_searching(self) -> bool:
        return self._running is not None

    @property
    def is_bending(self) -> bool:
        """Whether step 2 is on: the stem's tip can be dragged."""

        return self._bending

    def start(self, source_id: int, target_id: int, x: float, z: float) -> bool:
        """Starts a junction on the road through the connection."""

        autodrive_data = self.autodrive_data_provider()

        if autodrive_data is None or self.edit_history.history_locked or self.is_searching:
            return False

        self._lanes = road_lanes(autodrive_data, source_id, target_id)
        self._foot = foot_on_lane(self._lanes[0], (x, z))[:2]
        self._bending = False
        self.preview = None
        logger.debug(
            "Junction started on %d->%d, lanes %s",
            source_id,
            target_id,
            [(lane.node_ids[0], lane.node_ids[-1]) for lane in self._lanes],
        )

        return True

    def drag_to(self, x: float, z: float):
        """Step 1: previews the junction at the road point closest to (x, z), the stem square to
        the road towards (x, z) and reaching as far."""

        if self._foot is None or self._bending:
            return

        foot_x, foot_z, road_heading = foot_on_lane(self._lanes[0], (x, z))
        length = math.hypot(x - foot_x, z - foot_z)

        if length < 1e-6:
            return

        side = (z - foot_z) * math.cos(road_heading) - (x - foot_x) * math.sin(road_heading)
        heading = road_heading + math.copysign(math.pi / 2, side)
        self._foot = (foot_x, foot_z)
        gap = self._gap(None)
        junction = self._junction(heading, gap)
        autodrive_data = self.autodrive_data_provider()
        self._across = roads_across(autodrive_data, self._lanes, self._foot, heading)
        tip = (foot_x + length * math.cos(heading), foot_z + length * math.sin(heading))
        distance = math.dist(self._foot, junction[:2])
        tip = tip if length > distance else junction[:2]
        self._set_preview(self._plan(junction, gap), junction, tip, gap, None)

    def release(self) -> bool:
        """Ends step 1: the stem's tip can be dragged now. False (and cancelled) if there is
        nothing to bend."""

        if self.preview is None:
            self.cancel()
            return False

        self._bending = True

        return True

    def bend_to(self, x: float, z: float, node_id: int | None = None):
        """Step 2: bends the stem to the tip (x, z), or to the node `node_id` it then joins.
        With the Auto stem, joining a two-way road makes the stem two-way."""

        preview = self.preview

        if not self._bending or preview is None:
            return

        autodrive_data = self.autodrive_data_provider()

        if node_id is not None:
            node = autodrive_data.nodes[node_id]
            x, z = node.x, node.z

        gap = self._gap(node_id)
        junction, plan = preview.junction, preview.plan

        if gap != preview.gap:
            junction = self._junction(junction[2], gap)
            plan = self._plan(junction, gap)

        self._set_preview(plan, junction, (x, z), gap, node_id)

    def finish(self) -> bool:
        """Adds the previewed junction to the plan, once the curves that do not fit as drawn
        have been searched."""

        preview = self.preview
        self._bending = False

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
        logger.debug("Junction: searching %s", preview.plan.missing)

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
        self._across = []
        self._bending = False
        self.preview = None
        self.preview_changed.emit()

        return had_something

    def _gap(self, tip_id: int | None) -> float:
        """The lane gap of the stem, 0 for a two-way stem."""

        stem, gap = self.stem_provider()

        if stem == Stem.AUTO and tip_id is not None:
            if is_on_two_way_road(self.autodrive_data_provider(), tip_id):
                return 0.0

        return gap if uses_two_lanes(stem, self._lanes) else 0.0

    def _junction(self, heading: float, gap: float) -> Pose:
        distance = junction_distance(self._lanes, self._foot, heading, YARD_RADIUS, gap)

        return (
            self._foot[0] + distance * math.cos(heading),
            self._foot[1] + distance * math.sin(heading),
            heading,
        )

    def _set_preview(self, plan, junction: Pose, tip, gap: float, tip_id: int | None):
        stem = tuple(stem_poses(junction, tip, self.spacing_provider()))
        self.preview = JunctionPreview(plan, junction, stem, gap, tip_id)
        self.preview_changed.emit()

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
            self._across,
        )

    def _finish(self, plan: JunctionPlan | None):
        running, self._running = self._running, None
        self.searching_changed.emit(False)

        if plan is None or running is None or running["cancelled"].is_set():
            return

        preview = running["preview"]
        self._add(
            JunctionPreview(plan, preview.junction, preview.stem, preview.gap, preview.tip_id)
        )

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
            stem=list(preview.stem),
            gap=preview.gap,
            tip_id=preview.tip_id,
        )
        _log(preview, command)
        self.cancel()
        self.edit_history.push(command)

        if preview.plan.missing:
            self.status_changed.emit(
                tr("Junction added; missing: {missing}", missing=", ".join(preview.plan.missing))
            )
        else:
            self.status_changed.emit(tr("Junction added"))

        return True


def _log(preview: JunctionPreview, command):
    x, z, heading = preview.junction
    logger.debug(
        "Junction at (%.1f, %.1f) heading %.0f°, %s, stem %.1f m to (%.1f, %.1f), tip node %s",
        x,
        z,
        math.degrees(heading),
        f"two lanes {preview.gap:.1f} m apart" if preview.gap else "two-way",
        preview.stem_length,
        *preview.stem[-1][:2],
        preview.tip_id,
    )

    for curve in preview.plan.curves:
        end = curve.road_end
        x, z = end.point
        where = f"node {end.node_id}" if end.node_id is not None else f"split at ({x:.1f}, {z:.1f})"
        logger.debug(
            "  %s %s %s %d->%d: %s, radius %.0f m%s",
            "straight lane" if curve.across else "curve",
            curve.kind.value,
            "from lane" if curve.kind.value == "in" else "to lane",
            curve.lane.node_ids[0],
            curve.lane.node_ids[-1],
            where,
            curve.radius,
            ", searched" if curve.searched else "",
        )

    if preview.plan.missing:
        logger.debug("  missing: %s", ", ".join(preview.plan.missing))

    logger.debug("  %d new nodes, %d connections", len(command.new_nodes), len(command.connections))
