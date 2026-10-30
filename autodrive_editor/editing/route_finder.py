"""Route finder: a drivable route over the game's drivability map (see navigation_costmap).

Hybrid A*: the search moves in short arcs and straight pieces over position and heading, forward
only and no tighter than the turning radius, so a vehicle with a trailer can drive the route.
Close to each waypoint it tries a Dubins path, which ends exactly at the waypoint, and at the goal
heading at the last one. All waypoints are passed in one search, so the heading at a waypoint is
the one that suits the next leg too. The search is guided by the cheapest way from each cell to the
next waypoint, found on the cells alone first.

- Blocked cells cost so much that routes go a long way round them. Where there is no way round,
  the route crosses them and the crossing points are marked, so the editor can show where nodes
  have to move. Within half the vehicle width plus the safety margin of blocked cells each metre
  costs extra, so routes keep their distance where there is room but can still pass gates, which
  the map shows only about 3 m wide for a 4 m gate.
- Each metre costs by the kind of ground (roads and yards 1, grass 4, fields 8, …), so routes
  keep to roads and yards.
- Lanes already planned are cheap in their direction, so routes join them. Against their
  direction they cost more, so a way back gets its own lane where there is room and only shares
  the lane where there is not.
- Around the waypoints and along the start and goal headings, blocked cells can be driven on, as
  nodes may sit under a roof or in a hall.
"""

import heapq
import logging
import math
import time
from dataclasses import dataclass, field
from itertools import pairwise

from autodrive_editor.editing.dubins import Pose, advance, shortest_path
from autodrive_editor.file_io.navigation_costmap import BLOCKED_VALUE, ROAD_VALUE, NavigationCostmap

logger = logging.getLogger(__name__)

Point = tuple[float, float]
Lane = tuple[Point, Point]

# Length of one search step and the distance between checked points, in metres.
STEP = 2.0
SAMPLE = 0.5
HEADING_BINS = 72
# Size of the cells for visited states, in metres.
STATE_CELL = 1.0
# Extra cost per metre of turning, so straight pieces are preferred.
TURN_COST = 0.1
# Cost factor of planned lanes driven in their direction and against it.
SAME_LANE = 0.5
AGAINST_LANE = 1.5
# Headings within this cosine count as along a lane.
ALONG_LANE = 0.7
# Lanes are cheap only this close, so routes join them instead of running beside them.
ON_LANE = 1.0
# Cost of blocked cells near the waypoints.
FREE_ZONE_COST = 3.0
# Cost per metre of crossing blocked cells elsewhere.
OBSTACLE_COST = 100.0
# Extra cost per metre closer to a blocked cell than half the vehicle width plus the margin.
NEAR_BLOCKED_COST = 20.0
# Headings tried where any heading will do.
ANY_HEADINGS = tuple(math.tau * index / 16 for index in range(16))
# Dubins paths are tried this close to a waypoint, in turning radii plus metres.
DUBINS_RADII = 4
DUBINS_EXTRA = 20.0
# Area around the waypoints that is searched first, and how often it grows.
WINDOW_MARGIN = 60.0
WINDOW_GROWTH = (1, 3, 6)
# Search steps of one search, so the preview stays quick. Then the cheapest route found so far
# is taken; without one, the route goes on from the furthest point reached in direct curves
# through the remaining waypoints, which may cross blocked cells.
MAX_EXPANSIONS = 20_000
# The estimate to the goal counts this much more, so the search goes for the goal sooner;
# routes become a few percent longer than the cheapest.
HEURISTIC_WEIGHT = 1.2


@dataclass(frozen=True)
class Vehicle:
    turning_radius: float = 10.0
    width: float = 3.0
    margin: float = 0.5


@dataclass(frozen=True)
class RouteRequest:
    # Points the route passes in order, at least start and goal.
    waypoints: tuple[Point, ...]
    # Headings the route may start and end with, in radians; None for any heading.
    start_headings: tuple[float, ...] | None = None
    goal_headings: tuple[float, ...] | None = None
    # Planned lanes, each from its first to its second point.
    lanes: tuple[Lane, ...] = ()
    # Around the waypoints, and from the start forward and to the goal along their headings,
    # blocked cells can be driven on.
    free_radius: float = 3.0
    free_length: float = 20.0

    @property
    def start(self) -> Point:
        return self.waypoints[0]

    @property
    def goal(self) -> Point:
        return self.waypoints[-1]


@dataclass
class Route:
    points: list[Point]
    # Index in `points` of each waypoint.
    waypoint_indices: list[int]
    # For each point, whether it lies on a blocked cell outside the free zones.
    blocked: list[bool]

    @property
    def is_clear(self) -> bool:
        return not any(self.blocked)


class Grid:
    """Part of the drivability map with the blocked cells widened."""

    def __init__(self, costmap: NavigationCostmap, bounds: tuple[int, int, int, int], widen: float):
        first_column, first_row, end_column, end_row = bounds
        self.first_column, self.first_row = first_column, first_row
        self.columns = end_column - first_column
        self.rows = end_row - first_row
        self.half_width = costmap.width / 2
        self.half_height = costmap.height / 2

        rows = [costmap.row(row, first_column, end_column) for row in range(first_row, end_row)]
        self.cells = b"".join(rows)
        self.blocked = _widen_blocked(rows, self.columns, widen)

    def index(self, x: float, z: float) -> int | None:
        column = int(x + self.half_width) - self.first_column
        row = int(z + self.half_height) - self.first_row

        if 0 <= column < self.columns and 0 <= row < self.rows:
            return row * self.columns + column

        return None

    def center(self, index: int) -> Point:
        row, column = divmod(index, self.columns)

        return (
            column + self.first_column - self.half_width + 0.5,
            row + self.first_row - self.half_height + 0.5,
        )


BLOCKED_TABLE = bytes(1 if value >= BLOCKED_VALUE else 0 for value in range(256))
# Cost per metre of each band of cell values (see navigation_costmap): roads and yards, fields
# (expensive, to spare the crops), grass, then rougher ground.
BAND_COSTS = (1.0, 8.0, 4.0, 6.0, 8.0, 10.0)
BAND_WIDTH = 34


def cell_cost(value: int) -> float:
    """Cost per metre of a cell value. Steeper ground costs up to double within its band."""

    band, offset = divmod(max(0, value - ROAD_VALUE), BAND_WIDTH)

    return BAND_COSTS[min(band, len(BAND_COSTS) - 1)] * (1 + offset / BAND_WIDTH)


COST_TABLE = [cell_cost(value) for value in range(256)]


def _widen_blocked(rows: list[bytes], columns: int, widen: float) -> bytes:
    """One byte per cell, 1 where a cell lies within `widen` metres of a blocked cell. Each row is
    one big integer with a byte per cell, so the widening is done with shifts."""

    if not rows:
        return b""

    reach = max(0, math.ceil(widen - 0.5))
    full = (1 << (8 * columns)) - 1
    masks = [int.from_bytes(row.translate(BLOCKED_TABLE), "little") for row in rows]

    # Rows widened sideways by each needed number of cells.
    sideways: dict[int, list[int]] = {}

    for offset in range(reach + 1):
        cells = math.floor(math.sqrt(max(0.0, (reach + 0.5) ** 2 - offset * offset)))

        if cells in sideways:
            continue

        widened = []

        for mask in masks:
            result = mask

            for shift in range(1, cells + 1):
                result |= (mask << (8 * shift)) | (mask >> (8 * shift))

            widened.append(result & full)

        sideways[cells] = widened

    reaches = [
        math.floor(math.sqrt(max(0.0, (reach + 0.5) ** 2 - offset * offset)))
        for offset in range(reach + 1)
    ]
    result_rows = []

    for row in range(len(rows)):
        mask = 0

        for offset in range(-reach, reach + 1):
            other = row + offset

            if 0 <= other < len(rows):
                mask |= sideways[reaches[abs(offset)]][other]

        result_rows.append(mask.to_bytes(columns, "little"))

    return b"".join(result_rows)


@dataclass
class _Node:
    pose: Pose
    cost: float
    parent: "_Node | None"
    # Points driven from the parent to this pose, without the parent's.
    points: list[Point] = field(default_factory=list)
    curvature: float = 0.0
    # Index of the leg the node is on: leg k leads to waypoint k + 1.
    leg: int = 0
    # Whether the node is a waypoint reached by the route.
    at_waypoint: bool = False


class RouteFinder:
    def __init__(self, costmap: NavigationCostmap, vehicle: Vehicle):
        self.costmap = costmap
        self.vehicle = vehicle

    def find(self, request: RouteRequest, cancelled=lambda: False) -> Route | None:
        """The route through the waypoints with points about SAMPLE apart, or None if the search
        found none or was cancelled. The search area grows only while nothing is found; a detour
        further out can be forced with a waypoint."""

        self._log_request(request)
        route = None

        for growth in WINDOW_GROWTH:
            started = time.perf_counter()
            search = _Search(self, request, WINDOW_MARGIN * growth)
            route = search.run(cancelled)
            logger.debug(
                "Search window %d × %d m: %s, %d steps, %.2f s",
                search.grid.columns,
                search.grid.rows,
                search.outcome,
                search.expansions,
                time.perf_counter() - started,
            )

            if route is not None or cancelled() or search.covers_map:
                break

        return None if cancelled() else route

    def _log_request(self, request: RouteRequest):
        if not logger.isEnabledFor(logging.DEBUG):
            return

        def degrees(headings):
            if headings is None:
                return "any"

            return ", ".join(f"{math.degrees(heading) % 360:.0f}°" for heading in headings)

        logger.debug(
            "Route search through %s (cell values %s), start headings %s, goal headings %s, "
            "%d planned lanes, %s",
            ", ".join(_rounded(point) for point in request.waypoints),
            ", ".join(str(self.costmap.value_at(*point)) for point in request.waypoints),
            degrees(request.start_headings),
            degrees(request.goal_headings),
            len(request.lanes),
            self.vehicle,
        )


class _Search:
    def __init__(self, finder: RouteFinder, request: RouteRequest, margin: float):
        costmap, vehicle = finder.costmap, finder.vehicle
        self.request = request
        self.radius = vehicle.turning_radius

        xs = [x for x, _ in request.waypoints]
        zs = [z for _, z in request.waypoints]
        margin = max(margin, 2 * self.radius + 10)
        half_width, half_height = costmap.width / 2, costmap.height / 2
        bounds = (
            max(0, math.floor(min(xs) - margin + half_width)),
            max(0, math.floor(min(zs) - margin + half_height)),
            min(costmap.width, math.ceil(max(xs) + margin + half_width)),
            min(costmap.height, math.ceil(max(zs) + margin + half_height)),
        )
        self.covers_map = bounds == (0, 0, costmap.width, costmap.height)
        self.grid = Grid(costmap, bounds, vehicle.width / 2 + vehicle.margin)
        self.lanes = _lane_cells(self.grid, request.lanes, vehicle.width + vehicle.margin)
        self.free_corridors = _free_corridors(request)
        self.corridor_width = vehicle.width / 2 + vehicle.margin
        self.curvatures = (0.0, 0.5 / self.radius, -0.5 / self.radius, 1 / self.radius)
        self.curvatures += (-1 / self.radius,)
        # How the search ended and how many states it looked at, for the debug log.
        self.outcome = "not run"
        self.expansions = 0
        self._cell_costs: list[float] | None = None

    def run(self, cancelled) -> Route | None:
        request = self.request
        waypoints = request.waypoints
        legs = len(waypoints) - 1
        self.to_goal = [self._costs_to(waypoint) for waypoint in waypoints[1:]]
        # Cheapest cost over the cells from the end of each leg to the goal.
        self.remaining = [0.0] * legs

        for leg in range(legs - 2, -1, -1):
            self.remaining[leg] = self._estimate(waypoints[leg + 1], leg + 1)

        if self._estimate(request.start, 0) == math.inf:
            self.outcome = "no way over the cells through the waypoints"
            return None

        open_list = []
        best: dict[tuple, float] = {}
        counter = 0

        # Without given headings, straight towards the next waypoint is tried too.
        next_x, next_z = waypoints[1]
        towards = math.atan2(next_z - request.start[1], next_x - request.start[0])

        for heading in request.start_headings or (towards, *ANY_HEADINGS):
            node = _Node((*request.start, heading), 0.0, None, [request.start], at_waypoint=True)
            heapq.heappush(open_list, (self._estimate(request.start, 0), counter, node))
            counter += 1

        dubins_distance = DUBINS_RADII * self.radius + DUBINS_EXTRA
        expansions = 0
        max_expansions = MAX_EXPANSIONS
        # Cheapest end at the goal seen so far and the node furthest on the way, used when the
        # steps run out.
        best_end: _Node | None = None
        furthest: tuple[int, float, _Node] | None = None

        while open_list and expansions < max_expansions:
            _, _, node = heapq.heappop(open_list)
            key = self._key(node.pose, node.leg)

            if best.get(key, math.inf) < node.cost:
                continue

            expansions += 1
            self.expansions = expansions

            if expansions % 1000 == 0 and cancelled():
                self.outcome = "cancelled"
                return None

            if node.leg == legs:
                return self._found(node, "route found")

            progress = (node.leg, -self._estimate(node.pose, node.leg))

            if furthest is None or progress > furthest[:2]:
                furthest = (*progress, node)

            x, z, _ = node.pose
            target_x, target_z = waypoints[node.leg + 1]
            children = [self._step(node, curvature) for curvature in self.curvatures]

            if math.hypot(target_x - x, target_z - z) < dubins_distance:
                children.append(self._dubins_end(node))

            for child in children:
                if child is None:
                    continue

                child_key = self._key(child.pose, child.leg)

                if child.leg == legs and (best_end is None or child.cost < best_end.cost):
                    best_end = child

                if child.cost < best.get(child_key, math.inf):
                    best[child_key] = child.cost
                    estimate = HEURISTIC_WEIGHT * self._estimate(child.pose, child.leg)
                    heapq.heappush(open_list, (child.cost + estimate, counter, child))
                    counter += 1

        if best_end is not None:
            return self._found(best_end, f"cheapest route after {max_expansions} steps")

        if furthest is not None:
            end, start_index = self._direct_end(furthest[2])
            outcome = (
                f"stuck after {expansions} steps on leg {furthest[2].leg + 1}, "
                "direct curves from there"
            )
            return self._found(end, outcome, start_index)

        self.outcome = "every drivable pose tried (turning radius or safety distance too large?)"
        return None

    def _direct_end(self, node: _Node) -> tuple[_Node, int]:
        """The node continued by Dubins paths through the remaining waypoints, regardless of
        blocked cells, and the number of route points before the first of them. At each waypoint
        the heading points to the next one."""

        waypoints = self.request.waypoints
        start_index = len(self._route(node).points)

        for leg in range(node.leg + 1, len(waypoints)):
            x, z = waypoints[leg]

            if leg + 1 < len(waypoints):
                next_x, next_z = waypoints[leg + 1]
                heading = math.atan2(next_z - z, next_x - x)
            elif self.request.goal_headings:
                heading = self.request.goal_headings[0]
            else:
                heading = math.atan2(z - node.pose[1], x - node.pose[0])

            path = shortest_path(node.pose, (x, z, heading), self.radius)
            poses = path.sample(SAMPLE)[1:]
            points = [pose[:2] for pose in poses]
            length = sum(math.dist(a, b) for a, b in pairwise([node.pose[:2], *points]))
            node = _Node((x, z, heading), node.cost + length, node, points, 0.0, leg, True)

        return node, start_index

    def _found(self, end: _Node, outcome: str, direct_from: int | None = None) -> Route:
        route = self._route(end, direct_from)
        length = sum(math.dist(a, b) for a, b in pairwise(route.points))
        crossing = "" if route.is_clear else ", crosses blocked cells"
        self.outcome = f"{outcome}, {length:.0f} m, cost {end.cost:.0f}{crossing}"

        return route

    def _route(self, end: _Node, direct_from: int | None = None) -> Route:
        """The route to the node. Points from `direct_from` on were not searched, so there the
        safety distance to blocked cells counts as blocked too."""

        nodes = []
        node = end

        while node is not None:
            nodes.append(node)
            node = node.parent

        points: list[Point] = []
        waypoint_indices = []

        for node in reversed(nodes):
            points += node.points

            if node.at_waypoint:
                waypoint_indices.append(len(points) - 1)

        searched = len(points) if direct_from is None else direct_from
        blocked = [self._is_blocked(point, index >= searched) for index, point in enumerate(points)]

        return Route(points, waypoint_indices, blocked)

    def _is_blocked(self, point: Point, with_safety_distance: bool = False) -> bool:
        index = self.grid.index(*point)

        if index is None:
            return with_safety_distance

        if with_safety_distance:
            blocked = self.grid.blocked[index]
        else:
            blocked = self.grid.cells[index] >= BLOCKED_VALUE

        return bool(blocked) and not self._in_free_zone(*point)

    def _key(self, pose: Pose, leg: int) -> tuple[int, int, int, int]:
        x, z, heading = pose
        heading_bin = round(heading / math.tau * HEADING_BINS) % HEADING_BINS

        return math.floor(x / STATE_CELL), math.floor(z / STATE_CELL), heading_bin, leg

    def _estimate(self, position, leg: int) -> float:
        if leg == len(self.to_goal):
            return 0.0

        index = self.grid.index(position[0], position[1])

        return math.inf if index is None else self.to_goal[leg][index] + self.remaining[leg]

    def _costs_to(self, target: Point) -> list[float]:
        """Cheapest cost from each cell to the target over the cells, ignoring the turning radius.
        Dijkstra over the 8 neighbours of each cell; planned lanes count in the driving direction
        of each step."""

        grid = self.grid
        columns = grid.columns
        lanes = self.lanes
        if self._cell_costs is None:
            self._cell_costs = [self._ground_cost(index) for index in range(len(grid.cells))]

        cell_costs = self._cell_costs
        costs = [math.inf] * len(cell_costs)
        goal = grid.index(*target)

        if goal is None:
            return costs

        costs[goal] = 0.0
        queue = [(0.0, goal)]
        diagonal = math.sqrt(2)
        steps = [(-1, 0, 1.0), (1, 0, 1.0), (0, -1, 1.0), (0, 1, 1.0)]
        steps += [(-1, -1, diagonal), (1, -1, diagonal), (-1, 1, diagonal), (1, 1, diagonal)]

        while queue:
            cost, index = heapq.heappop(queue)

            if cost > costs[index]:
                continue

            row, column = divmod(index, columns)
            own = cell_costs[index]

            for d_column, d_row, length in steps:
                other_column, other_row = column + d_column, row + d_row

                if not (0 <= other_column < columns and 0 <= other_row < grid.rows):
                    continue

                other = other_row * columns + other_column
                step_cost = cell_costs[other]

                if step_cost == math.inf:
                    continue

                if index in lanes or other in lanes:
                    # The vehicle drives from the other cell to this one.
                    direction = (-d_column / length, -d_row / length)
                    step_cost *= self._lane_factor(other, *direction)
                    new_cost = (
                        cost + length * (own * self._lane_factor(index, *direction) + step_cost) / 2
                    )
                else:
                    new_cost = cost + length * (own + step_cost) / 2

                if new_cost < costs[other]:
                    costs[other] = new_cost
                    heapq.heappush(queue, (new_cost, other))

        return costs

    def _ground_cost(self, index: int, x: float | None = None, z: float | None = None) -> float:
        """Cost per metre of the cell's ground; inf if it cannot be driven on."""

        grid = self.grid
        value = grid.cells[index]

        if not grid.blocked[index]:
            return COST_TABLE[value]

        if x is None:
            x, z = grid.center(index)

        if self._in_free_zone(x, z):
            return FREE_ZONE_COST if value >= BLOCKED_VALUE else COST_TABLE[value]

        if value >= BLOCKED_VALUE:
            return OBSTACLE_COST

        return COST_TABLE[value] + NEAR_BLOCKED_COST

    def _lane_factor(self, index: int, direction_x: float, direction_z: float) -> float:
        """Cheaper on a planned lane in its direction, dearer near one against it."""

        lanes = self.lanes.get(index)

        if not lanes:
            return 1.0

        alignments = [
            (direction_x * lane_x + direction_z * lane_z, on_lane)
            for lane_x, lane_z, on_lane in lanes
        ]

        if any(alignment > ALONG_LANE and on_lane for alignment, on_lane in alignments):
            return SAME_LANE

        if any(alignment < -ALONG_LANE for alignment, _ in alignments):
            return AGAINST_LANE

        return 1.0

    def _step(self, node: _Node, curvature: float) -> _Node | None:
        points = []
        cost = node.cost
        pose = node.pose
        count = round(STEP / SAMPLE)

        for _ in range(count):
            pose = advance(pose, curvature, SAMPLE)
            piece = self._piece_cost(pose)

            if piece is None:
                return None

            cost += piece * SAMPLE
            points.append(pose[:2])

        if curvature:
            cost += TURN_COST * STEP

        return _Node(pose, cost, node, points, curvature, node.leg)

    def _piece_cost(self, pose: Pose) -> float | None:
        """Cost per metre at the pose, None if it cannot be driven on."""

        x, z, heading = pose
        index = self.grid.index(x, z)

        if index is None:
            return None

        cost = self._ground_cost(index, x, z)

        if cost == math.inf:
            return None

        if index in self.lanes:
            cost *= self._lane_factor(index, math.cos(heading), math.sin(heading))

        return cost

    def _in_free_zone(self, x: float, z: float) -> bool:
        radius = self.request.free_radius

        if any(math.hypot(x - px, z - pz) <= radius for px, pz in self.request.waypoints):
            return True

        return any(
            _distance_to_segment((x, z), a, b) <= self.corridor_width
            for a, b in self.free_corridors
        )

    def _dubins_end(self, node: _Node) -> _Node | None:
        """The next waypoint reached from the node by a Dubins path, if there is one. The given
        goal headings count only at the goal."""

        leg = node.leg + 1
        goal_x, goal_z = self.request.waypoints[leg]
        x, z, _ = node.pose
        headings = None

        if leg == len(self.request.waypoints) - 1:
            headings = self.request.goal_headings

        headings = headings or (math.atan2(goal_z - z, goal_x - x),)
        best = None

        for heading in headings:
            path = shortest_path(node.pose, (goal_x, goal_z, heading), self.radius)

            if path is None or (best is not None and path.length >= best[0].length):
                continue

            poses = path.sample(SAMPLE)[1:]
            cost = node.cost
            previous = node.pose

            for pose in poses:
                piece = self._piece_cost(pose)

                if piece is None:
                    break

                cost += piece * math.dist(previous[:2], pose[:2])
                previous = pose
            else:
                best = (path, cost, [pose[:2] for pose in poses], heading)

        if best is None:
            return None

        _, cost, points, heading = best

        return _Node((goal_x, goal_z, heading), cost, node, points, leg=leg, at_waypoint=True)


def _free_corridors(request: RouteRequest) -> list[Lane]:
    """Lines along which blocked cells can be driven on: from the start forward along each start
    heading and to the goal along each goal heading."""

    corridors = []
    length = request.free_length

    for (x, z), headings, sign in (
        (request.start, request.start_headings, 1),
        (request.goal, request.goal_headings, -1),
    ):
        for heading in headings or ():
            end = (x + sign * length * math.cos(heading), z + sign * length * math.sin(heading))
            corridors.append(((x, z), end))

    return corridors


def _lane_cells(
    grid: Grid, lanes: tuple[Lane, ...], reach: float
) -> dict[int, list[tuple[float, float, bool]]]:
    """Per cell within `reach` of planned lanes: the direction of each lane and whether the cell
    is on it (within ON_LANE)."""

    cells: dict[int, list[tuple[float, float, bool]]] = {}

    for (ax, az), (bx, bz) in lanes:
        length = math.hypot(bx - ax, bz - az)

        if length < 1e-6:
            continue

        direction = ((bx - ax) / length, (bz - az) / length)

        for x in range(math.floor(min(ax, bx) - reach), math.ceil(max(ax, bx) + reach) + 1):
            for z in range(math.floor(min(az, bz) - reach), math.ceil(max(az, bz) + reach) + 1):
                index = grid.index(x + 0.5, z + 0.5)

                if index is None:
                    continue

                distance = _distance_to_segment((x + 0.5, z + 0.5), (ax, az), (bx, bz))

                if distance <= reach:
                    cells.setdefault(index, []).append((*direction, distance <= ON_LANE))

    return cells


def _distance_to_segment(point: Point, a: Point, b: Point) -> float:
    abx, abz = b[0] - a[0], b[1] - a[1]
    length_squared = abx * abx + abz * abz
    t = 0.0

    if length_squared > 0:
        t = ((point[0] - a[0]) * abx + (point[1] - a[1]) * abz) / length_squared
        t = min(max(t, 0.0), 1.0)

    return math.hypot(point[0] - a[0] - t * abx, point[1] - a[1] - t * abz)


def _rounded(point: Point) -> str:
    return f"({point[0]:.1f}, {point[1]:.1f})"
