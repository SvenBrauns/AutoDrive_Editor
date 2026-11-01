"""Route finder: a drivable route over the game's drivability map (see navigation_costmap).

Hybrid A*: the search moves in short arcs and straight pieces over position and heading, forward
only and no tighter than the turning radius, so a vehicle with a trailer can drive the route.
Close to each waypoint it tries a Dubins path, which ends exactly at the waypoint, and at the goal
heading at the last one. All waypoints are passed in one search, so the heading at a waypoint is
the one that suits the next leg too. The search is guided by the cheapest way from each cell to the
next waypoint, found on the cells alone first. Changing from a left to a right turn costs extra,
and afterwards stretches of the route are replaced by Dubins paths (straight where the poses line
up) where these are no longer and no dearer, and lie on no worse ground and no closer to blocked
cells, so routes do not swerve.

- Blocked cells cost so much that routes go a long way round them. Where there is no way round,
  the route crosses them and the crossing points are marked, so the editor can show where nodes
  have to move. Within half the vehicle width plus the safety margin of blocked cells each metre
  costs extra, so routes keep their distance where there is room but can still pass gates, which
  the map shows only about 3 m wide for a 4 m gate.
- Each metre costs by the kind of ground (roads and yards 1, grass 4, fields 8, …), so routes
  keep to roads and yards.
- Each metre off the line between two waypoints costs a little extra, so where that line is clear
  the route runs along it and turns around the waypoints, as drawn by hand.
- Lanes already planned are cheap in their direction, so routes join them. Against their
  direction they cost more, so a way back gets its own lane where there is room and only shares
  the lane where there is not.
- Around the waypoints and along the start and goal headings, blocked cells can be driven on, as
  nodes may sit under a roof or in a hall.

Routes never loop. Where the waypoints lie too close for the turning radius, nothing is searched;
where the search finds no way on, the route ends there. Both leave a gap (see Route.gap).
"""

import heapq
import logging
import math
import time
from collections import deque
from dataclasses import dataclass, field
from itertools import pairwise

from autodrive_editor.editing.dubins import TURNS, DubinsPath, Pose, advance, shortest_path
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
# Extra cost of changing from a left to a right turn or back, so routes do not swerve from side
# to side.
SWERVE_COST = 1.0
# Extra cost per metre for each metre off the line between the two waypoints of a leg, counted up
# to CHORD_REACH, so routes keep to that line where it is clear. Not within CHORD_FREE turning
# radii of the waypoints, where the route turns.
CHORD_COST = 0.1
CHORD_REACH = 4.0
CHORD_FREE = 1.5
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
# There, paths onto the line between the waypoints are tried too, joining it this many turning
# radii further on.
LINE_JOINS = (1.0, 2.0, 3.0, 4.0)
# Area around the waypoints that is searched first, and how often it grows. It grows only when
# the search found no complete route and tried to leave the area.
WINDOW_MARGIN = 60.0
WINDOW_GROWTH = (1, 3, 6)
# Search steps of one search, so the preview stays quick. Then the cheapest route found so far
# is taken; without one, the route ends at the furthest point reached.
MAX_EXPANSIONS = 20_000
# A route turning this far one way within LOOP_CIRCLES turning circles of length has a loop.
# Less, so a roundabout or a drive around a large building is no loop.
LOOP_TURN = math.radians(300)
LOOP_CIRCLES = 2
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
    # Tightest turn of this search, e.g. the yard radius; None for the vehicle's.
    turning_radius: float | None = None

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
    # Where no drivable connection was found: straight from the last point through the
    # waypoints not reached, the first of them waypoint number `gap_to`. Empty when complete.
    gap: list[Point] = field(default_factory=list)
    gap_to: int = 0
    # Whether the gap is there because two waypoints lie too close for the turning radius; then
    # nothing was searched and the gap runs from waypoint `gap_to - 1` to `gap_to`.
    too_close: bool = False

    @property
    def is_complete(self) -> bool:
        return not self.gap

    @property
    def is_clear(self) -> bool:
        return self.is_complete and not any(self.blocked)


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
BAND_COSTS = (1.0, 8.0, 2.0, 6.0, 8.0, 10.0)
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
        was cancelled. A route that does not reach all waypoints has a gap. The search area grows
        only while the search runs into its edge; a detour further out can be forced with a
        waypoint."""

        self._log_request(request)
        radius = request.turning_radius or self.vehicle.turning_radius
        leg = _too_close_leg(request, radius)

        if leg is not None:
            logger.debug("Waypoints %d and %d too close for the radius", leg + 1, leg + 2)
            gap = list(request.waypoints[leg : leg + 2])
            return Route([], [], [], gap, leg + 1, too_close=True)

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

            if cancelled() or search.covers_map or not search.hit_edge:
                break

            if route is not None and route.is_complete:
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
            "%d planned lanes, turning radius %s, %s",
            ", ".join(_rounded(point) for point in request.waypoints),
            ", ".join(str(self.costmap.value_at(*point)) for point in request.waypoints),
            degrees(request.start_headings),
            degrees(request.goal_headings),
            len(request.lanes),
            request.turning_radius or "of the vehicle",
            self.vehicle,
        )


class _Search:
    def __init__(self, finder: RouteFinder, request: RouteRequest, margin: float):
        costmap, vehicle = finder.costmap, finder.vehicle
        self.request = request
        self.radius = request.turning_radius or vehicle.turning_radius

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
        # Whether the search tried to leave the area.
        self.hit_edge = False
        self._cell_costs: list[float] | None = None

    def run(self, cancelled) -> Route | None:
        request = self.request
        waypoints = request.waypoints
        legs = len(waypoints) - 1
        self.to_goal = []

        for leg in range(legs):
            costs = self._costs_to(leg, cancelled)

            if costs is None:
                self.outcome = "cancelled"
                return None

            self.to_goal.append(costs)

        # Cheapest cost over the cells from the end of each leg to the goal.
        self.remaining = [0.0] * legs

        for leg in range(legs - 2, -1, -1):
            self.remaining[leg] = self._estimate(waypoints[leg + 1], leg + 1)

        if self._estimate(request.start, 0) == math.inf:
            self.outcome = "no way over the cells through the waypoints"
            start = _Node((*request.start, 0.0), 0.0, None, [request.start], at_waypoint=True)
            return self._with_gap(self._route(start), 1)

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
            outcome = f"stuck after {expansions} steps on leg {furthest[2].leg + 1}"
            return self._found(furthest[2], outcome)

        self.outcome = "every drivable pose tried (turning radius or safety distance too large?)"
        return None

    def _found(self, end: _Node, outcome: str) -> Route:
        """The route to the node, straightened, and up to a loop if it has one. A gap leads on
        through the waypoints not reached."""

        route = self._route(self._straighten(end))
        loop = _loop_start(route.points, LOOP_CIRCLES * math.tau * self.radius)

        if loop is not None:
            reached = [index for index in route.waypoint_indices if index <= loop]
            route = Route(route.points[: loop + 1], reached, route.blocked[: loop + 1])
            outcome += f", cut before a loop at {_rounded(route.points[-1])}"

        if len(route.waypoint_indices) < len(self.request.waypoints):
            route = self._with_gap(route, len(route.waypoint_indices))

        length = sum(math.dist(a, b) for a, b in pairwise(route.points))
        crossing = "" if not any(route.blocked) else ", crosses blocked cells"
        gap = f", gap to waypoint {route.gap_to + 1}" if route.gap else ""
        self.outcome = f"{outcome}, {length:.0f} m, cost {end.cost:.0f}{crossing}{gap}"

        return route

    def _with_gap(self, route: Route, gap_to: int) -> Route:
        route.gap = [route.points[-1], *self.request.waypoints[gap_to:]]
        route.gap_to = gap_to

        return route

    def _route(self, end: _Node) -> Route:
        """The route to the node."""

        points: list[Point] = []
        waypoint_indices = []

        for node in _chain(end):
            points += node.points

            if node.at_waypoint:
                waypoint_indices.append(len(points) - 1)

        blocked = [self._is_blocked(point) for point in points]

        return Route(points, waypoint_indices, blocked)

    def _straighten(self, end: _Node) -> _Node:
        """The route to the node with stretches replaced by Dubins paths, which run straight
        where the poses line up. A replacement is no longer and costs no more than the stretch,
        lies on no worse ground and no closer to blocked cells, and passes no waypoint."""

        nodes = _chain(end)
        lengths = [0.0]

        for previous, node in pairwise(nodes):
            points = [previous.pose[:2], *node.points]
            lengths.append(lengths[-1] + sum(math.dist(a, b) for a, b in pairwise(points)))

        worst = [self._worst_ground(node.points) for node in nodes]
        result = nodes[0]
        index = 0

        while index < len(nodes) - 1:
            limit = index + 1

            while limit < len(nodes) - 1 and not nodes[limit].at_waypoint:
                limit += 1

            # The furthest good shortcut: doubling the reach until one fails, then halving.
            found, good, bad, span = None, index, limit + 1, 1

            while good < limit:
                target = min(index + span, limit)
                candidate = self._shortcut(nodes, lengths, worst, index, target)

                if candidate is None:
                    bad = target
                    break

                found, good, span = candidate, target, span * 2

            while bad - good > 1:
                target = (good + bad) // 2
                candidate = self._shortcut(nodes, lengths, worst, index, target)

                if candidate is None:
                    bad = target
                else:
                    found, good = candidate, target

            if found is None:
                good = index + 1
                node = nodes[good]
                cost = result.cost + node.cost - nodes[index].cost
                points, curvature = node.points, node.curvature
            else:
                cost, points, curvature = result.cost + found[0], found[1], found[2]
                node = nodes[good]

            result = _Node(node.pose, cost, result, points, curvature, node.leg, node.at_waypoint)
            index = good

        return result

    def _shortcut(
        self,
        nodes: list[_Node],
        lengths: list[float],
        worst: list[tuple[int, float]],
        first: int,
        last: int,
    ) -> tuple[float, list[Point], float] | None:
        """Cost, points and last curvature of the Dubins path from node `first` to node `last` if
        it may replace the stretch between them (see _straighten), else None. `lengths` holds
        the route length up to each node, `worst` its worst ground (see _worst_ground)."""

        start, end = nodes[first], nodes[last]
        length = lengths[last] - lengths[first]
        worst = worst[first + 1 : last + 1]
        path = shortest_path(start.pose, end.pose, self.radius)

        if path is None or path.length > length + 1e-6 or _is_loop(path):
            return None

        most_blocked = max(blocked for blocked, _ in worst)
        worst_ground = max(ground for _, ground in worst)
        limit = end.cost - start.cost + 1e-6
        cost = _turning_cost(path, start.curvature, self.radius)
        points = []
        previous = start.pose

        for pose in path.sample(SAMPLE)[1:]:
            blocked, ground = self._ground_class(pose)
            piece = self._piece_cost(pose, start.leg)

            if piece is None or blocked > most_blocked or ground > worst_ground:
                return None

            cost += piece * math.dist(previous[:2], pose[:2])

            if cost > limit:
                return None

            points.append(pose[:2])
            previous = pose

        curvature = next(
            (
                TURNS[letter] / self.radius
                for letter, part in zip(reversed(path.word), reversed(path.lengths), strict=True)
                if part > 1e-9
            ),
            0.0,
        )

        return cost, points, curvature

    def _worst_ground(self, points: list[Point]) -> tuple[int, float]:
        """Highest blocked class and ground class of the points (see _ground_class)."""

        classes = [self._ground_class(point) for point in points] or [(0, 0.0)]

        return max(blocked for blocked, _ in classes), max(ground for _, ground in classes)

    def _ground_class(self, position) -> tuple[int, float]:
        """How blocked the cell is (0 free, 1 within the safety distance, 2 blocked; free zones
        count as free) and the base cost of its kind of ground, without the slope."""

        index = self.grid.index(position[0], position[1])

        if index is None:
            return 2, math.inf

        value = self.grid.cells[index]
        band = min(max(0, value - ROAD_VALUE) // BAND_WIDTH, len(BAND_COSTS) - 1)
        blocked = 0

        if self.grid.blocked[index] and not self._in_free_zone(position[0], position[1]):
            blocked = 2 if value >= BLOCKED_VALUE else 1

        return blocked, BAND_COSTS[band]

    def _is_blocked(self, point: Point) -> bool:
        index = self.grid.index(*point)

        if index is None:
            return False

        return self.grid.cells[index] >= BLOCKED_VALUE and not self._in_free_zone(*point)

    def _key(self, pose: Pose, leg: int) -> tuple[int, int, int, int]:
        x, z, heading = pose
        heading_bin = round(heading / math.tau * HEADING_BINS) % HEADING_BINS

        return math.floor(x / STATE_CELL), math.floor(z / STATE_CELL), heading_bin, leg

    def _estimate(self, position, leg: int) -> float:
        if leg == len(self.to_goal):
            return 0.0

        index = self.grid.index(position[0], position[1])

        return math.inf if index is None else self.to_goal[leg][index] + self.remaining[leg]

    def _costs_to(self, leg: int, cancelled=lambda: False) -> list[float] | None:
        """Cheapest cost from each cell to the end of the leg over the cells, ignoring the turning
        radius; None if cancelled. Dijkstra over the 8 neighbours of each cell; planned lanes
        count in the driving direction of each step, and the distance to the leg's line counts
        as on the route."""

        grid = self.grid
        columns = grid.columns
        lanes = self.lanes
        if self._cell_costs is None:
            self._cell_costs = [self._ground_cost(index) for index in range(len(grid.cells))]

        cell_costs = self._with_chord_costs(self._cell_costs, leg)
        costs = [math.inf] * len(cell_costs)
        goal = grid.index(*self.request.waypoints[leg + 1])

        if goal is None:
            return costs

        costs[goal] = 0.0
        queue = [(0.0, goal)]
        diagonal = math.sqrt(2)
        steps = [(-1, 0, 1.0), (1, 0, 1.0), (0, -1, 1.0), (0, 1, 1.0)]
        steps += [(-1, -1, diagonal), (1, -1, diagonal), (-1, 1, diagonal), (1, 1, diagonal)]
        popped = 0

        while queue:
            cost, index = heapq.heappop(queue)

            if cost > costs[index]:
                continue

            popped += 1

            if popped % 10_000 == 0 and cancelled():
                return None

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

    def _with_chord_costs(self, cell_costs: list[float], leg: int) -> list[float]:
        """The cell costs plus the chord cost of each cell on the leg (see _chord_cost). Only
        cells near the leg's line are measured; the rest get the full chord cost."""

        grid = self.grid
        a, b = self.request.waypoints[leg : leg + 2]
        costs = [cost + CHORD_COST * CHORD_REACH for cost in cell_costs]
        margin = max(CHORD_REACH, CHORD_FREE * self.radius)
        xs = range(math.floor(min(a[0], b[0]) - margin), math.ceil(max(a[0], b[0]) + margin) + 1)
        zs = range(math.floor(min(a[1], b[1]) - margin), math.ceil(max(a[1], b[1]) + margin) + 1)

        for z in zs:
            for x in xs:
                index = grid.index(x + 0.5, z + 0.5)

                if index is not None:
                    costs[index] = cell_costs[index] + self._chord_cost(*grid.center(index), leg)

        return costs

    def _chord_cost(self, x: float, z: float, leg: int) -> float:
        """Extra cost per metre off the line between the leg's waypoints. None near the
        waypoints, where the route turns."""

        a, b = self.request.waypoints[leg : leg + 2]
        free = CHORD_FREE * self.radius

        if math.hypot(x - a[0], z - a[1]) < free or math.hypot(x - b[0], z - b[1]) < free:
            return 0.0

        return CHORD_COST * min(_distance_to_segment((x, z), a, b), CHORD_REACH)

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
            piece = self._piece_cost(pose, node.leg)

            if piece is None:
                return None

            cost += piece * SAMPLE
            points.append(pose[:2])

        if curvature:
            cost += TURN_COST * STEP

        if curvature * node.curvature < 0:
            cost += SWERVE_COST

        return _Node(pose, cost, node, points, curvature, node.leg)

    def _piece_cost(self, pose: Pose, leg: int) -> float | None:
        """Cost per metre at the pose on the leg, None if it cannot be driven on."""

        x, z, heading = pose
        index = self.grid.index(x, z)

        if index is None:
            self.hit_edge = True
            return None

        cost = self._ground_cost(index, x, z)

        if cost == math.inf:
            return None

        if index in self.lanes:
            cost *= self._lane_factor(index, math.cos(heading), math.sin(heading))

        return cost + self._chord_cost(x, z, leg)

    def _in_free_zone(self, x: float, z: float) -> bool:
        radius = self.request.free_radius

        if any(math.hypot(x - px, z - pz) <= radius for px, pz in self.request.waypoints):
            return True

        return any(
            _distance_to_segment((x, z), a, b) <= self.corridor_width
            for a, b in self.free_corridors
        )

    def _dubins_end(self, node: _Node) -> _Node | None:
        """The next waypoint reached from the node by a Dubins path, or by one onto the line
        between the leg's waypoints and along it, whichever is cheaper. The given goal headings
        count only at the goal."""

        leg = node.leg + 1
        waypoints = self.request.waypoints
        goal_x, goal_z = waypoints[leg]
        x, z, _ = node.pose
        headings = None

        if leg == len(waypoints) - 1:
            headings = self.request.goal_headings

        candidates = []

        for heading in headings or (math.atan2(goal_z - z, goal_x - x),):
            path = shortest_path(node.pose, (goal_x, goal_z, heading), self.radius)

            if path is not None and not _is_loop(path):
                candidates.append((heading, path.sample(SAMPLE)[1:]))

        if not headings:
            candidates += self._onto_line(node)

        best = None

        for heading, poses in candidates:
            cost = node.cost
            previous = node.pose

            for pose in poses:
                piece = self._piece_cost(pose, node.leg)

                if piece is None:
                    break

                cost += piece * math.dist(previous[:2], pose[:2])
                previous = pose
            else:
                if best is None or cost < best[0]:
                    best = (cost, heading, [pose[:2] for pose in poses])

        if best is None:
            return None

        cost, heading, points = best

        return _Node((goal_x, goal_z, heading), cost, node, points, leg=leg, at_waypoint=True)

    def _onto_line(self, node: _Node) -> list[tuple[float, list[Pose]]]:
        """For each of LINE_JOINS: the heading of the line between the leg's waypoints and the
        poses of a Dubins path from the node onto that line, that many turning radii further on,
        then along it to the next waypoint. Only joins before the waypoint."""

        (ax, az), (bx, bz) = self.request.waypoints[node.leg : node.leg + 2]
        length = math.hypot(bx - ax, bz - az)
        x, z, _ = node.pose

        if length < 1e-6:
            return []

        dx, dz = (bx - ax) / length, (bz - az) / length
        heading = math.atan2(dz, dx)
        candidates = []

        for join in LINE_JOINS:
            along = (x - ax) * dx + (z - az) * dz + join * self.radius

            if along >= length:
                break

            goal = (ax + along * dx, az + along * dz, heading)
            path = shortest_path(node.pose, goal, self.radius)

            if path is None or _is_loop(path):
                continue

            rest = length - along
            count = max(1, math.ceil(rest / SAMPLE))
            straight = [
                (bx - rest * (1 - k / count) * dx, bz - rest * (1 - k / count) * dz, heading)
                for k in range(1, count + 1)
            ]
            candidates.append((heading, path.sample(SAMPLE)[1:] + straight))

        return candidates


def _chain(end: _Node) -> list[_Node]:
    """The nodes from the start to the node."""

    nodes = []

    while end is not None:
        nodes.append(end)
        end = end.parent

    return nodes[::-1]


def _turning_cost(path: DubinsPath, curvature: float, radius: float) -> float:
    """Turning and swerving costs of the path as the search counts them, coming from a piece
    with the given curvature."""

    cost = 0.0

    for letter, length in zip(path.word, path.lengths, strict=True):
        if length <= 1e-9:
            continue

        part = TURNS[letter] / radius
        if part * curvature < 0:
            cost += SWERVE_COST

        if part:
            cost += TURN_COST * length
            curvature = part

    return cost


def _is_loop(path: DubinsPath) -> bool:
    """Whether the Dubins path has a loop (see LOOP_TURN)."""

    turning = sum(
        length for letter, length in zip(path.word, path.lengths, strict=True) if letter != "S"
    )

    if turning < LOOP_TURN * path.radius:
        return False

    points = [pose[:2] for pose in path.sample(path.radius / 4)]

    return _loop_start(points, LOOP_CIRCLES * math.tau * path.radius) is not None


def _loop_start(points: list[Point], reach: float) -> int | None:
    """Index of the point where the first loop begins: from there, the heading turns LOOP_TURN
    or more one way within `reach` metres. None without a loop."""

    headings, starts, indices = [], [], []
    along = 0.0

    for index, (a, b) in enumerate(pairwise(points)):
        length = math.dist(a, b)

        if length < 1e-9:
            continue

        heading = math.atan2(b[1] - a[1], b[0] - a[0])

        if headings:
            # Unwrapped, so turning on keeps adding up.
            heading = headings[-1] + math.remainder(heading - headings[-1], math.tau)

        headings.append(heading)
        starts.append(along)
        indices.append(index)
        along += length

    # Pieces within reach before the current one, with rising and with falling headings, so the
    # first holds the lowest heading and the last the highest.
    lowest: deque[int] = deque()
    highest: deque[int] = deque()

    for piece, heading in enumerate(headings):
        for queue in (lowest, highest):
            while queue and starts[piece] - starts[queue[0]] > reach:
                queue.popleft()

        while lowest and headings[lowest[-1]] >= heading:
            lowest.pop()

        while highest and headings[highest[-1]] <= heading:
            highest.pop()

        lowest.append(piece)
        highest.append(piece)

        if heading - headings[lowest[0]] >= LOOP_TURN:
            return indices[lowest[0]]

        if headings[highest[0]] - heading >= LOOP_TURN:
            return indices[highest[0]]

    return None


def _too_close_leg(request: RouteRequest, radius: float) -> int | None:
    """The first leg whose waypoints lie too close for the radius: every way between them with
    the headings possible there has a loop, even ignoring the ground. None if all legs can be
    driven. Free headings are tried in ANY_HEADINGS and towards the next waypoint."""

    waypoints = request.waypoints
    last = len(waypoints) - 1
    headings = None

    for leg in range(last):
        (ax, az), (bx, bz) = waypoints[leg], waypoints[leg + 1]
        towards = math.atan2(bz - az, bx - ax)

        if headings is None:
            headings = request.start_headings or (towards, *ANY_HEADINGS)

        ends = request.goal_headings if leg + 1 == last else None
        reachable = []

        for end in ends or (towards, *ANY_HEADINGS):
            for start in headings:
                path = shortest_path((ax, az, start), (bx, bz, end), radius)

                if path is not None and not _is_loop(path):
                    reachable.append(end)
                    break

        if not reachable:
            return leg

        headings = reachable

    return None


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
