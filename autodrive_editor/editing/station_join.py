"""Direct joins: the lane of a stop joined straight to the nearest road.

The road is the connection closest to the stop within the reach that is neither subprio nor
touches a marker. As with the in and out halves of the junction template, a leg leads in from
each lane of that road (both directions where it has two) to the start of the stop's lane, and
one leads out from its end to each lane. Legs are Dubins curves where these are clear on the
drivability map, else searched with the route finder (only when find_route is given); a leg that
does not fit is listed and shown as a gap. Leg nodes are subprio like the lane and spaced as
AutoDrive records; a road connection is split where a leg leaves or joins it, keeping its type.
"""

import math
from collections.abc import Callable
from dataclasses import dataclass, field
from itertools import pairwise

from autodrive_editor.editing.commands.add_route import AddRouteCommand
from autodrive_editor.editing.dubins import Pose
from autodrive_editor.editing.junction import (
    Curve,
    CurveKind,
    _curve_connections,
    _distance_to_segment,
    plan_junction,
    road_lanes,
    split_connections,
)
from autodrive_editor.editing.route_finder import Route, RouteRequest, Vehicle
from autodrive_editor.editing.route_nodes import _recorded
from autodrive_editor.editing.station_layout import (
    StationSettings,
    StopChoice,
    direction,
    lane_points,
)
from autodrive_editor.file_io.navigation_costmap import NavigationCostmap
from autodrive_editor.i18n import tr
from autodrive_editor.model.autodrive_data import (
    SUBPRIO_FLAG,
    AutoDriveData,
    MarkerData,
    NodeData,
)
from autodrive_editor.model.connections import (
    CONNECTION_STATES,
    ConnectionType,
    is_reverse_connection,
)

Point = tuple[float, float]

# A leg may turn this much in all, as an S-curve or a hairpin, but never a full circle.
MAX_TURN = math.radians(270)


@dataclass
class StopJoin:
    """The legs of one stop, the legs that do not fit as text and as lines between their ends."""

    curves: list[Curve] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    gaps: list[tuple[Point, Point]] = field(default_factory=list)

    @property
    def has_way_in(self) -> bool:
        return any(curve.kind == CurveKind.IN for curve in self.curves)

    @property
    def has_way_out(self) -> bool:
        return any(curve.kind == CurveKind.OUT for curve in self.curves)


def nearest_road(
    autodrive_data: AutoDriveData, point: Point, reach: float
) -> tuple[int, int] | None:
    """The road connection (source, target) closest to the point within reach, or None."""

    nodes, markers = autodrive_data.nodes, autodrive_data.markers
    x, z = point
    best = None

    for node in nodes.values():
        if abs(node.x - x) > reach + 50 or abs(node.z - z) > reach + 50:
            continue

        if node.flag == SUBPRIO_FLAG or node.node_id in markers:
            continue

        for target_id in node.outgoing:
            target = nodes.get(target_id)

            if target is None or target.flag == SUBPRIO_FLAG or target_id in markers:
                continue

            if is_reverse_connection(node, target):
                continue

            distance = _distance_to_segment(point, (node.x, node.z), (target.x, target.z))

            if distance <= reach and (best is None or distance < best[0]):
                best = (distance, node.node_id, target_id)

    return None if best is None else best[1:]


def lane_poses(choice: StopChoice, settings: StationSettings) -> tuple[Pose, Pose]:
    """The poses where the legs meet the lane, as the junction template takes them: its start
    heading along the lane, its end heading back along it (into the "yard")."""

    points, _ = lane_points(choice.stop, settings, choice.heading)
    dx, dz = direction(choice.heading)
    heading = math.atan2(dz, dx)
    (sx, _, sz), (ex, _, ez) = points[0], points[-1]

    return (sx, sz, heading), (ex, ez, heading + math.pi)


def plan_direct(
    autodrive_data: AutoDriveData,
    choice: StopChoice,
    settings: StationSettings,
    radius: float,
    costmap: NavigationCostmap | None,
    vehicle: Vehicle,
    find_route: Callable[[RouteRequest], Route | None] | None = None,
) -> StopJoin:
    """The legs between the stop's lane and the nearest road."""

    x, _, z = choice.stop.position
    road = nearest_road(autodrive_data, (x, z), settings.reach)

    if road is None:
        return StopJoin(missing=[tr("No road within {reach} m", reach=f"{settings.reach:g}")])

    lanes = road_lanes(autodrive_data, *road)
    markers = frozenset(autodrive_data.markers)
    join = StopJoin()

    for kind, pose in zip((CurveKind.IN, CurveKind.OUT), lane_poses(choice, settings), strict=True):
        plan = plan_junction(
            lanes, pose, (kind,), radius, costmap, vehicle, markers, find_route, max_turn=MAX_TURN
        )
        join.curves += plan.curves
        join.missing += plan.missing
        join.gaps += plan.gaps

    return join


def direct_command(
    autodrive_data: AutoDriveData,
    choices: list[StopChoice],
    joins: list[StopJoin],
    settings: StationSettings,
    height_for_new_node: Callable[[AutoDriveData, float, float], float],
) -> tuple[AddRouteCommand, list[int]]:
    """The edit that adds the lanes, their markers and legs, and the IDs of the lane ends that
    still have no way in or out."""

    next_id = max(autodrive_data.nodes, default=0) + 1
    new_nodes: dict[int, NodeData] = {}

    def new_node(point: Point, y: float | None = None) -> int:
        nonlocal next_id

        if y is None:
            y = height_for_new_node(autodrive_data, *point)

        new_nodes[next_id] = NodeData(next_id, point[0], y, point[1], SUBPRIO_FLAG)
        next_id += 1

        return next_id - 1

    regular = CONNECTION_STATES[ConnectionType.REGULAR]
    splits: dict = {}
    connections, markers, open_ends = [], [], []

    def spaced(points: list[Point]) -> list[Point]:
        return _recorded(points, settings.spacing)

    for choice, join in zip(choices, joins, strict=True):
        points, marker_index = lane_points(choice.stop, settings, choice.heading)
        lane = [new_node((x, z), y) for x, y, z in points]
        connections += [(a, b, regular) for a, b in pairwise(lane)]
        markers.append(MarkerData(lane[marker_index], choice.name, choice.group))

        for kind, pose, node_id in zip(
            (CurveKind.IN, CurveKind.OUT),
            lane_poses(choice, settings),
            (lane[0], lane[-1]),
            strict=True,
        ):
            curves = [curve for curve in join.curves if curve.kind == kind]

            if not curves:
                open_ends.append(node_id)

            connections += _curve_connections(
                curves, pose, node_id, settings.spacing, splits, new_node, spaced
            )

    # Nodes splitting a road keep the road's type.
    for (source_id, _), points in splits.items():
        for _, _, node_id in points:
            new_nodes[node_id].flag = autodrive_data.nodes[source_id].flag

    connections += split_connections(autodrive_data, splits)
    command = AddRouteCommand(
        tr("Create station lanes"), autodrive_data, list(new_nodes.values()), connections, markers
    )

    return command, open_ends
