"""Direct joins: the lane of a stop joined to the nearest road through the yard.

From the start of the lane backwards and from its end forwards, a search over the drivability map
finds the cheapest way to a road (a connection that is neither subprio nor touches a marker):
ground other than roads and yards costs OFF_ROAD_FACTOR times more, so the way follows the yard
to its driveway. On a road of the map scan (a public road) a junction is placed there as with
the junction template, with curves in from or out to each lane of the road (both directions where
it has two); one junction serves both ways when they reach the road at the same place. Other
roads (stems and yard roads built before) are joined with one curve from or to the lane
reached. The yard leg between junction and lane is built by the route finder on the same costs;
for a quick preview it is the way itself, simplified. A leg or curve that does not fit is listed
and shown as a gap. Yard legs and curves are regular, the lane subprio; nodes are spaced as
AutoDrive records, and a road connection is split where a curve leaves or joins it, keeping its
type.
"""

import heapq
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
    foot_on_lane,
    junction_distance,
    plan_junction,
    road_lanes,
    split_connections,
)
from autodrive_editor.editing.planned_piece import PlannedPiece
from autodrive_editor.editing.route_finder import (
    BAND_WIDTH,
    COST_TABLE,
    Grid,
    Route,
    RouteRequest,
    Vehicle,
)
from autodrive_editor.editing.route_nodes import _recorded
from autodrive_editor.editing.station_layout import (
    StationSettings,
    StopChoice,
    direction,
    lane_points,
    plan_stations,
)
from autodrive_editor.file_io.navigation_costmap import BLOCKED_VALUE, ROAD_VALUE, NavigationCostmap
from autodrive_editor.i18n import tr
from autodrive_editor.model.autodrive_data import (
    MAP_SCAN_FLAG,
    REGULAR_FLAG,
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

# Ground other than roads and yards costs this many times more on the way to the road.
OFF_ROAD_FACTOR = 10.0
# Extra cost per metre close to blocked cells (within half the vehicle width plus margin).
NEAR_BLOCKED_COST = 5.0
# Blocked cells count as free this close to the lane end and beyond it along the lane, as lanes
# may lie under a roof: FREE_LENGTH past the last blocked cell, at most MAX_FREE_LENGTH. The lane
# itself (LANE_WIDTH wide) is closed to the search, so the way in leaves behind the lane and the
# way out ahead of it.
FREE_RADIUS = 3.0
FREE_LENGTH = 10.0
MAX_FREE_LENGTH = 80.0
LANE_WIDTH = 2.0
# The search area reaches this much further than the reach to a road.
SEARCH_MARGIN = 20.0
# The heading into the yard at a driveway is measured towards the way this far from the road.
INTO_YARD = 8.0
# The preview's yard legs leave out points of the way this close to a straight line.
PREVIEW_TOLERANCE = 1.0
# The ways in and out share one junction when their junctions are this close.
SHARED_JUNCTION = 12.0

STEPS = [(dx, dz, math.hypot(dx, dz)) for dx in (-1, 0, 1) for dz in (-1, 0, 1) if dx or dz]


@dataclass
class Driveway:
    """A junction where legs leave or join the road: its pose heading into the yard, its curves,
    and its node when it is built."""

    pose: Pose
    curves: list[Curve] = field(default_factory=list)


@dataclass
class YardLeg:
    """The way from a driveway's junction to the start of the lane (IN) or from the end of the
    lane to the junction (OUT), in driving order."""

    kind: CurveKind
    driveway: int
    points: list[Point]


@dataclass
class StopJoin:
    driveways: list[Driveway] = field(default_factory=list)
    legs: list[YardLeg] = field(default_factory=list)
    # What does not fit, as text and as lines between the ends.
    missing: list[str] = field(default_factory=list)
    gaps: list[tuple[Point, Point]] = field(default_factory=list)

    @property
    def has_way_in(self) -> bool:
        return self._has_way(CurveKind.IN)

    @property
    def has_way_out(self) -> bool:
        return self._has_way(CurveKind.OUT)

    def _has_way(self, kind: CurveKind) -> bool:
        return any(
            leg.kind == kind
            and any(curve.kind == kind for curve in self.driveways[leg.driveway].curves)
            for leg in self.legs
        )


def is_road(autodrive_data: AutoDriveData, source_id: int, target_id: int) -> bool:
    """Whether a new piece may join the connection: neither node subprio nor a marker."""

    nodes, markers = autodrive_data.nodes, autodrive_data.markers
    source, target = nodes.get(source_id), nodes.get(target_id)

    return (
        source is not None
        and target is not None
        and SUBPRIO_FLAG not in (source.flag, target.flag)
        and not {source_id, target_id} & markers.keys()
        and not is_reverse_connection(source, target)
    )


def nearest_road(
    autodrive_data: AutoDriveData, point: Point, reach: float
) -> tuple[int, int] | None:
    """The road connection (source, target) closest to the point within reach, or None."""

    x, z = point
    best = None

    for node, target in _road_connections(autodrive_data, point, reach):
        distance = _distance_to_segment(point, (node.x, node.z), (target.x, target.z))

        if distance <= reach and (best is None or distance < best[0]):
            best = (distance, node.node_id, target.node_id)

    return None if best is None else best[1:]


def _road_connections(autodrive_data: AutoDriveData, point: Point, distance: float):
    """(source, target) nodes of the road connections whose box lies within the distance."""

    x, z = point

    for node in autodrive_data.nodes.values():
        for target_id in node.outgoing:
            target = autodrive_data.nodes.get(target_id)

            if target is None or min(node.x, target.x) > x + distance:
                continue

            if max(node.x, target.x) < x - distance or min(node.z, target.z) > z + distance:
                continue

            if max(node.z, target.z) < z - distance:
                continue

            if is_road(autodrive_data, node.node_id, target_id):
                yield node, target


def lane_poses(choice: StopChoice, settings: StationSettings) -> tuple[Pose, Pose]:
    """The start and end of the lane with its heading (radians in the x-z plane)."""

    points, _ = lane_points(choice.stop, settings, choice.heading)
    dx, dz = direction(choice.heading)
    heading = math.atan2(dz, dx)
    (sx, _, sz), (ex, _, ez) = points[0], points[-1]

    return (sx, sz, heading), (ex, ez, heading)


def plan_direct(
    autodrive_data: AutoDriveData,
    choice: StopChoice,
    settings: StationSettings,
    radius: float,
    costmap: NavigationCostmap | None,
    vehicle: Vehicle,
    find_route: Callable[[RouteRequest], Route | None] | None = None,
) -> StopJoin:
    """The driveways and yard legs between the stop's lane and the road. Without find_route the
    yard legs follow the ways found (a quick preview)."""

    start, end = lane_poses(choice, settings)
    search = _WaySearch(autodrive_data, choice, settings, costmap, vehicle)
    join = StopJoin()
    ways = {}

    for kind, pose in ((CurveKind.IN, start), (CurveKind.OUT, end)):
        way = search.way(pose, kind)

        if way is None:
            reach = f"{settings.reach:g}"
            join.missing.append(
                tr("No way in from a road within {reach} m", reach=reach)
                if kind == CurveKind.IN
                else tr("No way out to a road within {reach} m", reach=reach)
            )
        else:
            ways[kind] = way

    markers = frozenset(autodrive_data.markers)

    for kind, (points, road, free_length) in ways.items():
        lanes = road_lanes(autodrive_data, *road)

        if not all(autodrive_data.nodes[node_id].flag == MAP_SCAN_FLAG for node_id in road):
            lanes = lanes[:1]

        junction = _junction(lanes, points, radius)
        shared = [
            index
            for index, driveway in enumerate(join.driveways)
            if math.dist(driveway.pose[:2], junction[:2]) < SHARED_JUNCTION
        ]

        if shared:
            index = shared[0]
            junction = join.driveways[index].pose
        else:
            index = len(join.driveways)
            join.driveways.append(Driveway(junction))

        plan = plan_junction(
            lanes, junction, (kind,), radius, costmap, vehicle, markers, find_route
        )
        join.driveways[index].curves += plan.curves
        join.missing += plan.missing
        join.gaps += plan.gaps
        lane_pose = start if kind == CurveKind.IN else end
        if find_route is None:
            leg = _way_leg(kind, points, junction)
        else:
            leg = _yard_leg(kind, junction, lane_pose, radius, free_length, find_route)

        if leg is None:
            join.missing.append(
                tr("No way in through the yard")
                if kind == CurveKind.IN
                else tr("No way out through the yard")
            )
            join.gaps.append((junction[:2], lane_pose[:2]))
        else:
            join.legs.append(YardLeg(kind, index, leg))

    return join


def _junction(lanes, points: list[Point], radius: float) -> Pose:
    """The junction where the way (from the lane to the road) meets the road: past the road far
    enough for the curves, heading into the yard along the way."""

    foot = foot_on_lane(lanes[0], points[-1])[:2]
    walked, toward = 0.0, points[0]

    for a, b in pairwise(reversed(points)):
        walked += math.dist(a, b)

        if walked >= INTO_YARD:
            toward = b
            break

    heading = math.atan2(toward[1] - foot[1], toward[0] - foot[0])
    distance = junction_distance(lanes, foot, heading, radius)

    return (
        foot[0] + distance * math.cos(heading),
        foot[1] + distance * math.sin(heading),
        heading,
    )


def _way_leg(kind: CurveKind, points: list[Point], junction: Pose) -> list[Point]:
    """The way from the lane end to the point closest to the junction, then to the junction,
    simplified, in driving order."""

    closest = min(range(len(points)), key=lambda index: math.dist(points[index], junction[:2]))
    leg = _simplified([*points[: closest + 1], junction[:2]], PREVIEW_TOLERANCE)

    return leg[::-1] if kind == CurveKind.IN else leg


def _simplified(points: list[Point], tolerance: float) -> list[Point]:
    """The points without those closer than the tolerance to the line between their
    neighbours that are kept (Douglas-Peucker)."""

    if len(points) < 3:
        return list(points)

    first, last = points[0], points[-1]
    index, distance = max(
        ((i, _distance_to_segment(points[i], first, last)) for i in range(1, len(points) - 1)),
        key=lambda item: item[1],
    )

    if distance <= tolerance:
        return [first, last]

    return _simplified(points[: index + 1], tolerance)[:-1] + _simplified(points[index:], tolerance)


def _yard_leg(
    kind: CurveKind,
    junction: Pose,
    lane: Pose,
    radius: float,
    free_length: float,
    find_route: Callable[[RouteRequest], Route | None],
) -> list[Point] | None:
    if kind == CurveKind.IN:
        start, goal = junction, lane
    else:
        start, goal = lane, (junction[0], junction[1], junction[2] + math.pi)

    request = RouteRequest(
        (start[:2], goal[:2]),
        (start[2],),
        (goal[2],),
        free_length=free_length,
        turning_radius=radius,
        off_road_factor=OFF_ROAD_FACTOR,
    )
    route = find_route(request)

    return list(route.points) if route is not None and route.is_complete else None


class _WaySearch:
    """The cheapest way over the cells from a lane end to a road (see the module text)."""

    def __init__(
        self,
        autodrive_data: AutoDriveData,
        choice: StopChoice,
        settings: StationSettings,
        costmap: NavigationCostmap | None,
        vehicle: Vehicle,
    ):
        self.autodrive_data = autodrive_data
        self.reach = settings.reach
        self.costmap = costmap
        x, _, z = choice.stop.position
        self.center = (x, z)
        self.lane = lane_poses(choice, settings)
        self.grid = None

        if costmap is not None:
            margin = settings.reach + SEARCH_MARGIN
            half_width, half_height = costmap.width / 2, costmap.height / 2
            bounds = (
                max(0, math.floor(x - margin + half_width)),
                max(0, math.floor(z - margin + half_height)),
                min(costmap.width, math.ceil(x + margin + half_width)),
                min(costmap.height, math.ceil(z + margin + half_height)),
            )
            self.grid = Grid(costmap, bounds, vehicle.width / 2 + vehicle.margin)
            self.roads = self._road_cells()

    def way(self, pose: Pose, kind: CurveKind) -> tuple[list[Point], tuple[int, int], float] | None:
        """The way from the lane end to the road as points (lane end first), the road
        connection it reaches and how far beyond the lane end blocked cells count as free, or
        None."""

        sign = -1 if kind == CurveKind.IN else 1
        dx, dz = sign * math.cos(pose[2]), sign * math.sin(pose[2])
        free_length = FREE_LENGTH

        if self.costmap is not None:
            covered = 0.0

            for step in range(1, int(MAX_FREE_LENGTH)):
                if self.costmap.value_at(pose[0] + step * dx, pose[1] + step * dz) >= BLOCKED_VALUE:
                    covered = step

            free_length = min(MAX_FREE_LENGTH, covered + FREE_LENGTH) if covered else FREE_LENGTH

        if self.grid is None:
            road = nearest_road(self.autodrive_data, pose[:2], self.reach)

            if road is None:
                return None

            nodes = self.autodrive_data.nodes
            a, b = nodes[road[0]], nodes[road[1]]
            mouth = _closest_on_segment(pose[:2], (a.x, a.z), (b.x, b.z))
            return [pose[:2], mouth], road, free_length

        grid = self.grid
        start = grid.index(*pose[:2])

        if start is None:
            return None

        beyond = (pose[0] + free_length * dx, pose[1] + free_length * dz)
        (sx, sz, _), (ex, ez, _) = self.lane
        costs = {start: 0.0}
        previous = {start: start}
        queue = [(0.0, start)]
        reach_cost = (self.reach + SEARCH_MARGIN) * OFF_ROAD_FACTOR * 3

        while queue:
            cost, index = heapq.heappop(queue)

            if cost > costs.get(index, math.inf) or cost > reach_cost:
                continue

            if index in self.roads and index != start:
                return self._points(previous, index, pose), self.roads[index], free_length

            row, column = divmod(index, grid.columns)

            for dx, dz, length in STEPS:
                other_column, other_row = column + dx, row + dz

                if not (0 <= other_column < grid.columns and 0 <= other_row < grid.rows):
                    continue

                other = other_row * grid.columns + other_column
                point = grid.center(other)
                free = math.dist(point, pose[:2]) <= FREE_RADIUS
                free = free or _distance_to_segment(point, pose[:2], beyond) <= FREE_RADIUS

                if not free and _distance_to_segment(point, (sx, sz), (ex, ez)) <= LANE_WIDTH:
                    continue

                value = grid.cells[other]

                if value >= BLOCKED_VALUE and not free:
                    continue

                if value >= BLOCKED_VALUE:
                    step = COST_TABLE[ROAD_VALUE]
                else:
                    step = COST_TABLE[value]

                    if value > ROAD_VALUE + BAND_WIDTH - 1:
                        step *= OFF_ROAD_FACTOR

                if grid.blocked[other] and not free:
                    step += NEAR_BLOCKED_COST

                new_cost = cost + length * step

                if new_cost < costs.get(other, math.inf):
                    costs[other] = new_cost
                    previous[other] = index
                    heapq.heappush(queue, (new_cost, other))

        return None

    def _points(self, previous: dict, index: int, pose: Pose) -> list[Point]:
        cells = [index]

        while previous[cells[-1]] != cells[-1]:
            cells.append(previous[cells[-1]])

        source_id, target_id = self.roads[index]
        nodes = self.autodrive_data.nodes
        a, b = nodes[source_id], nodes[target_id]
        mouth = _closest_on_segment(self.grid.center(index), (a.x, a.z), (b.x, b.z))

        return [pose[:2], *(self.grid.center(cell) for cell in reversed(cells[1:-1])), mouth]

    def _road_cells(self) -> dict[int, tuple[int, int]]:
        """The cells road connections run through, with their connection."""

        grid = self.grid
        margin = self.reach + SEARCH_MARGIN
        cells = {}

        for node, target in _road_connections(self.autodrive_data, self.center, margin):
            length = math.hypot(target.x - node.x, target.z - node.z)
            count = max(1, math.ceil(length / 0.5))

            for step in range(count + 1):
                fraction = step / count
                index = grid.index(
                    node.x + fraction * (target.x - node.x),
                    node.z + fraction * (target.z - node.z),
                )

                if index is not None:
                    cells.setdefault(index, (node.node_id, target.node_id))

        return cells


def _closest_on_segment(point: Point, a: Point, b: Point) -> Point:
    dx, dz = b[0] - a[0], b[1] - a[1]
    length = dx * dx + dz * dz
    fraction = 0.0 if length == 0 else ((point[0] - a[0]) * dx + (point[1] - a[1]) * dz) / length
    fraction = min(1.0, max(0.0, fraction))

    return (a[0] + fraction * dx, a[1] + fraction * dz)


def direct_command(
    autodrive_data: AutoDriveData,
    choices: list[StopChoice],
    joins: list[StopJoin],
    settings: StationSettings,
    height_for_new_node: Callable[[AutoDriveData, float, float], float],
) -> tuple[AddRouteCommand, list[int]]:
    """The edit that adds the lanes, their markers, driveways and yard legs, and the IDs of the
    lane ends that still have no way in or out."""

    next_id = max(autodrive_data.nodes, default=0) + 1
    new_nodes: dict[int, NodeData] = {}

    def new_node(point: Point, y: float | None = None, flag: int = REGULAR_FLAG) -> int:
        nonlocal next_id

        if y is None:
            y = height_for_new_node(autodrive_data, *point)

        new_nodes[next_id] = NodeData(next_id, point[0], y, point[1], flag)
        next_id += 1

        return next_id - 1

    regular = CONNECTION_STATES[ConnectionType.REGULAR]
    splits: dict = {}
    connections, markers, open_ends = [], [], []

    def spaced(points: list[Point]) -> list[Point]:
        return _recorded(points, settings.spacing)

    for choice, join in zip(choices, joins, strict=True):
        points, marker_index = lane_points(choice.stop, settings, choice.heading)
        lane = [new_node((x, z), y, SUBPRIO_FLAG) for x, y, z in points]
        connections += [(a, b, regular) for a, b in pairwise(lane)]
        markers.append(MarkerData(lane[marker_index], choice.name, choice.group))
        junction_ids = []

        for driveway in join.driveways:
            junction_ids.append(new_node(driveway.pose[:2]))
            connections += _curve_connections(
                driveway.curves,
                driveway.pose,
                junction_ids[-1],
                settings.spacing,
                splits,
                new_node,
                spaced,
            )

        for leg in join.legs:
            inner = [new_node(point) for point in spaced(leg.points)[1:-1]]
            junction_id = junction_ids[leg.driveway]

            if leg.kind == CurveKind.IN:
                chain = [junction_id, *inner, lane[0]]
            else:
                chain = [lane[-1], *inner, junction_id]

            connections += [(a, b, regular) for a, b in pairwise(chain)]

        if not join.has_way_in:
            open_ends.append(lane[0])

        if not join.has_way_out:
            open_ends.append(lane[-1])

    # Nodes splitting a road keep the road's type.
    for (source_id, _), points in splits.items():
        for _, _, node_id in points:
            new_nodes[node_id].flag = autodrive_data.nodes[source_id].flag

    connections += split_connections(autodrive_data, splits)
    command = AddRouteCommand(
        tr("Create station lanes"), autodrive_data, list(new_nodes.values()), connections, markers
    )

    return command, open_ends


def preview_piece(
    choices: list[StopChoice], joins: list[StopJoin], settings: StationSettings
) -> PlannedPiece:
    """The lanes with their driveways and yard legs, for the map while the dialog is open."""

    piece = plan_stations(choices, settings)

    for index, join in enumerate(joins):
        start, end = piece.open_ends[2 * index], piece.open_ends[2 * index + 1]
        y = piece.points[start][1]
        junctions = [piece.add(x, y, z) for x, z, _ in (d.pose for d in join.driveways)]

        for driveway, junction in zip(join.driveways, junctions, strict=True):
            for curve in driveway.curves:
                points = _recorded(list(curve.points), settings.spacing)
                ids = [piece.add(x, y, z) for x, z in points[1:-1]]

                if curve.kind == CurveKind.IN:
                    piece.chain([piece.add(*_xyz(points[0], y)), *ids, junction])
                else:
                    piece.chain([junction, *ids, piece.add(*_xyz(points[-1], y))])

        for leg in join.legs:
            ids = [piece.add(x, y, z) for x, z in _recorded(leg.points, settings.spacing)[1:-1]]

            if leg.kind == CurveKind.IN:
                piece.chain([junctions[leg.driveway], *ids, start])
            else:
                piece.chain([end, *ids, junctions[leg.driveway]])

    return piece


def _xyz(point: Point, y: float) -> tuple[float, float, float]:
    return point[0], y, point[1]
