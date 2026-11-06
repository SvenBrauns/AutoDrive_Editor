"""Route legs built the way courses are drawn by hand: straight pieces and arcs (see
route_geometry), then checked against the drivability map.

Per leg, first a direct try: turn, straight, turn with the end headings, like a Dubins path. Where
that does not lie on roads and yards only, a rough path over the cells (A* with the route finder's
costs) from a lead-in along the start heading to a lead-out along the goal heading. The rough path
is cut down to the few corners it needs: a straight piece replaces a stretch of it where it costs
no more and lies on no worse ground and no closer to blocked cells. Its corners are rounded with
arcs. The cheapest leg that passes the check is taken: no blocked cells or cells within the safety
distance outside the free zones.

The costs come from the route finder's search (route_finder._Search), so both agree.
"""

import heapq
import math
from dataclasses import dataclass

from autodrive_editor.editing.routes.dubins import Pose
from autodrive_editor.editing.routes.route_geometry import (
    MAX_ARC,
    Piece,
    Point,
    corners_of,
    fillet,
    sample,
    turn_straight_turn,
)

# Lead-in and lead-out along the end headings, in radii.
LEAD = 1.0
# Cost per metre of roads and yards; a direct try on them alone needs no rough path.
CHEAPEST_GROUND = 1.0
# A straight piece may cost this much more than the stretch of the rough path it replaces, as the
# cells' costs are counted a little differently.
SHORTCUT_TOLERANCE = 1.03
# Where an arc fails the check, its corner is pushed outwards this far, at most this often.
PUSH = 0.5
MAX_PUSHES = 12
# How often the rough path search looks whether it was cancelled.
CANCEL_CHECK = 10_000

STEPS = [(-1, 0, 1.0), (1, 0, 1.0), (0, -1, 1.0), (0, 1, 1.0)]
STEPS += [(dx, dz, math.sqrt(2)) for dx in (-1, 1) for dz in (-1, 1)]


@dataclass
class Leg:
    points: list[Point]
    end_heading: float
    cost: float
    # How the leg was built, for the debug log.
    kind: str = ""


class LegBuilder:
    def __init__(self, search, radius: float, step: float, cheapest: float):
        """`search` gives the costs and the grid (route_finder._Search); `step` is the distance
        of the points; `cheapest` the lowest cost per metre on the grid (planned lanes count)."""

        self.search = search
        self.grid = search.grid
        self.radius = radius
        self.step = step
        self.cheapest = cheapest

    def build(
        self,
        start: Point,
        start_headings: tuple[float, ...] | None,
        goal: Point,
        goal_headings: tuple[float, ...] | None,
        cancelled=lambda: False,
    ) -> Leg | None:
        """The cheapest leg that passes the check, over all given headings; None if there is
        none or the search was cancelled."""

        best = None

        for start_heading in start_headings or (None,):
            for goal_heading in goal_headings or (None,):
                leg = self._build(start, start_heading, goal, goal_heading, cancelled)

                if leg is not None and (best is None or leg.cost < best.cost):
                    best = leg

        return best

    def _build(self, start, start_heading, goal, goal_heading, cancelled) -> Leg | None:
        best = None

        for corners in direct_corners(start, start_heading, goal, goal_heading, self.radius):
            leg = self._checked(corners, "direct")

            if leg is not None and (best is None or leg.cost < best.cost):
                best = leg

        if best is not None and not self.search.lanes and self._on_cheapest_ground(best.points):
            return best

        lead_in = (
            start if start_heading is None else _ahead(start, start_heading, LEAD * self.radius)
        )
        lead_out = goal if goal_heading is None else _ahead(goal, goal_heading, -LEAD * self.radius)
        rough = self._rough_path(lead_in, lead_out, cancelled)

        if rough is not None:
            # The lead-in and lead-out stay, so the leg keeps the end headings.
            corners = self._simplified(*rough)
            fixed = set()

            if start_heading is not None:
                corners.insert(0, start)
                fixed.add(1)

            if goal_heading is not None:
                corners.append(goal)
                fixed.add(len(corners) - 2)

            corners = self._without_needless_corners(corners, fixed)
            worst_ground = max(self.search._ground_class(point)[1] for point in rough[0])
            leg = self._checked(corners, "rough path", worst_ground)

            if leg is not None and (best is None or leg.cost < best.cost):
                best = leg

        return best

    def _checked(
        self, corners: list[Point], kind: str, worst_ground: float = math.inf
    ) -> Leg | None:
        """The leg through the corners with rounded corners and its cost, or None if it cannot
        be rounded or fails the check (see _piece_cost). Where an arc fails, its corner is pushed
        outwards, as arcs cut the corners and the corner itself is on good ground."""

        for _ in range(MAX_PUSHES + 1):
            pieces = fillet(corners, self.radius)

            if not pieces:
                return None

            points = [pieces[0].start[:2]]
            cost = 0.0
            failed = None

            for number, piece in enumerate(pieces):
                for point in sample([piece], self.step)[1:]:
                    piece_cost = self._piece_cost(points[-1], point, worst_ground)

                    if piece_cost is None:
                        failed = number
                        break

                    points.append(point)
                    cost += piece_cost

                if failed is not None:
                    break
            else:
                return Leg(points, pieces[-1].end[2], cost, kind)

            if not pieces[failed].curvature:
                return None

            corners = corners_of(pieces)
            corner = 1 + sum(1 for piece in pieces[:failed] if piece.curvature)
            corners[corner] = _pushed(corners[corner], pieces[failed])

        return None

    def _piece_cost(self, a: Point, b: Point, worst_ground: float = math.inf) -> float | None:
        """Cost of driving from a to b at b's cell; None on a blocked cell or one within the
        safety distance outside the free zones, on ground worse than `worst_ground` (see
        _Search._ground_class), or off the grid."""

        search, grid = self.search, self.grid
        index = grid.index(*b)

        if index is None or grid.blocked[index] and not search._in_free_zone(*b):
            return None

        if worst_ground < math.inf and search._ground_class(b)[1] > worst_ground:
            return None

        length = math.dist(a, b)
        cost = search._ground_cost(index, *b)

        if index in search.lanes:
            cost *= search._lane_factor(index, (b[0] - a[0]) / length, (b[1] - a[1]) / length)

        return cost * length

    def _on_cheapest_ground(self, points: list[Point]) -> bool:
        return all(self.search._ground_class(point)[1] <= CHEAPEST_GROUND for point in points)

    def _rough_path(
        self, start: Point, goal: Point, cancelled
    ) -> tuple[list[Point], list[float]] | None:
        """The cheapest path over the cells from start to goal (A*, 8 neighbours) as cell centres
        with the exact start and goal, and the cost up to each; None if there is none."""

        search, grid = self.search, self.grid
        columns, rows = grid.columns, grid.rows
        first, last = grid.index(*start), grid.index(*goal)

        if first is None or last is None:
            return None

        goal_row, goal_column = divmod(last, columns)
        lanes = search.lanes
        cell_costs: dict[int, float] = {}

        def cell_cost(index: int) -> float:
            cost = cell_costs.get(index)

            if cost is None:
                cost = cell_costs[index] = search._ground_cost(index)

            return cost

        def estimate(index: int) -> float:
            row, column = divmod(index, columns)
            d_row, d_column = abs(row - goal_row), abs(column - goal_column)
            diagonal = min(d_row, d_column)

            return self.cheapest * (max(d_row, d_column) - diagonal + math.sqrt(2) * diagonal)

        costs = {first: 0.0}
        parents: dict[int, int] = {}
        queue = [(estimate(first), 0.0, first)]
        popped = 0

        while queue:
            _, cost, index = heapq.heappop(queue)

            if index == last:
                break

            if cost > costs[index]:
                continue

            popped += 1

            if popped % CANCEL_CHECK == 0 and cancelled():
                return None

            row, column = divmod(index, columns)
            own = cell_cost(index)

            for d_column, d_row, length in STEPS:
                other_column, other_row = column + d_column, row + d_row

                if not (0 <= other_column < columns and 0 <= other_row < rows):
                    continue

                other = other_row * columns + other_column
                step_cost = cell_cost(other)

                if step_cost == math.inf:
                    continue

                if lanes and (index in lanes or other in lanes):
                    direction = (d_column / length, d_row / length)
                    own_part = own * search._lane_factor(index, *direction)
                    step_cost *= search._lane_factor(other, *direction)
                    new_cost = cost + length * (own_part + step_cost) / 2
                else:
                    new_cost = cost + length * (own + step_cost) / 2

                if new_cost < costs.get(other, math.inf):
                    costs[other] = new_cost
                    parents[other] = index
                    heapq.heappush(queue, (new_cost + estimate(other), new_cost, other))
        else:
            return None

        cells = [last]

        while cells[-1] != first:
            cells.append(parents[cells[-1]])

        cells.reverse()
        points = [grid.center(index) for index in cells]
        points[0], points[-1] = start, goal

        return points, [costs[index] for index in cells]

    def _simplified(self, points: list[Point], costs: list[float]) -> list[Point]:
        """The corners of the rough path that are needed: from each corner, the furthest point
        that a straight piece can reach (see _shortcut_fits); the first and last point stay."""

        classes = [self.search._ground_class(point) for point in points]
        corners = [points[0]]
        index = 0

        while index < len(points) - 1:
            # Doubling the reach until a shortcut fails, then halving.
            good, bad, span = index + 1, len(points), 2

            while index + span < len(points):
                if not self._shortcut_fits(points, costs, classes, index, index + span):
                    bad = index + span
                    break

                good, span = index + span, span * 2
            else:
                if self._shortcut_fits(points, costs, classes, index, len(points) - 1):
                    good = len(points) - 1
                else:
                    bad = len(points) - 1

            while bad - good > 1:
                middle = (good + bad) // 2

                if self._shortcut_fits(points, costs, classes, index, middle):
                    good = middle
                else:
                    bad = middle

            corners.append(points[good])
            index = good

        return corners

    def _shortcut_fits(self, points, costs, classes, first: int, last: int) -> bool:
        """Whether a straight piece may replace the rough path from point `first` to `last`: it
        costs no more and lies on no worse ground and no closer to blocked cells."""

        if last - first < 2:
            return True

        stretch = classes[first + 1 : last + 1]
        limits = (
            (costs[last] - costs[first]) * SHORTCUT_TOLERANCE + 1e-6,
            max(blocked for blocked, _ in stretch),
            max(ground for _, ground in stretch),
        )

        return self._measured(points[first], points[last], limits) is not None

    def _without_needless_corners(self, corners: list[Point], fixed: set[int]) -> list[Point]:
        """The corners without those a straight piece can replace (see _shortcut_fits), except
        the first, the last and the `fixed` ones."""

        corners = list(corners)
        fixed = {0, len(corners) - 1, *fixed}
        index = 1

        while index < len(corners) - 1:
            if index in fixed:
                index += 1
                continue

            before, corner, after = corners[index - 1 : index + 2]
            first, second = self._measured(before, corner), self._measured(corner, after)
            limits = (
                (first[0] + second[0]) * SHORTCUT_TOLERANCE + 1e-6,
                max(first[1], second[1]),
                max(first[2], second[2]),
            )

            if self._measured(before, after, limits) is None:
                index += 1
                continue

            del corners[index]
            fixed = {item - (item > index) for item in fixed}
            index = max(1, index - 1)

        return corners

    def _measured(self, a: Point, b: Point, limits=None) -> tuple[float, int, float] | None:
        """Cost, highest blocked class and worst ground (see _Search._ground_class) of a straight
        piece; None if it is off the grid or exceeds the limits, given in the same order."""

        length = math.dist(a, b)
        count = max(1, math.ceil(length / self.step))
        cost, most_blocked, worst_ground = 0.0, 0, 0.0
        previous = a

        for k in range(1, count + 1):
            point = (a[0] + (b[0] - a[0]) * k / count, a[1] + (b[1] - a[1]) * k / count)
            index = self.grid.index(*point)

            if index is None:
                return None

            blocked, ground = self.search._ground_class(point)
            piece = self.search._ground_cost(index, *point)

            if index in self.search.lanes:
                direction = ((b[0] - a[0]) / length, (b[1] - a[1]) / length)
                piece *= self.search._lane_factor(index, *direction)

            cost += piece * math.dist(previous, point)
            most_blocked, worst_ground = max(most_blocked, blocked), max(worst_ground, ground)
            previous = point

            if limits is not None and (
                cost > limits[0] or most_blocked > limits[1] or worst_ground > limits[2]
            ):
                return None

        return cost, most_blocked, worst_ground


def direct_corners(
    start: Point, start_heading: float | None, goal: Point, goal_heading: float | None, radius
) -> list[list[Point]]:
    """Corner points of the direct ways from start to goal: a straight line, or turn and straight
    where one heading is given, or turn, straight, turn where both are (the Dubins paths without
    a middle arc), each turn less than half a circle."""

    if start_heading is None and goal_heading is None:
        return [[start, goal]]

    if goal_heading is None:
        return [
            [start, corner, goal] for corner in _turn_corners((*start, start_heading), goal, radius)
        ]

    if start_heading is None:
        backwards = (*goal, goal_heading + math.pi)
        return [[start, corner, goal] for corner in _turn_corners(backwards, start, radius)]

    ways = turn_straight_turn((*start, start_heading), (*goal, goal_heading), radius)

    return [[start, first, second, goal] for first, second in ways]


def _turn_corners(pose: Pose, goal: Point, radius: float) -> list[Point]:
    """Corner points of the ways from the pose to the goal that turn left or right at the radius,
    then run straight to the goal."""

    x, z, heading = pose
    corners = []

    for side in (1, -1):
        center_x = x - side * radius * math.sin(heading)
        center_z = z + side * radius * math.cos(heading)
        distance = math.hypot(goal[0] - center_x, goal[1] - center_z)

        if distance < radius:
            continue

        towards = math.atan2(goal[1] - center_z, goal[0] - center_x)
        straight = towards + side * math.asin(radius / distance)
        turn = (side * (straight - heading)) % math.tau

        if turn < MAX_ARC:
            corners.append(_ahead((x, z), heading, radius * math.tan(turn / 2)))

    return corners


def _pushed(corner: Point, arc: Piece) -> Point:
    """The corner moved PUSH metres away from the centre of its arc."""

    x, z, heading = arc.start
    center_x = x - math.sin(heading) / arc.curvature
    center_z = z + math.cos(heading) / arc.curvature
    distance = math.hypot(corner[0] - center_x, corner[1] - center_z)

    return (
        corner[0] + PUSH * (corner[0] - center_x) / distance,
        corner[1] + PUSH * (corner[1] - center_z) / distance,
    )


def bisector(before: Point, waypoint: Point, after: Point) -> float:
    """The heading halfway between the lines into and out of the waypoint."""

    into = math.atan2(waypoint[1] - before[1], waypoint[0] - before[0])
    out = math.atan2(after[1] - waypoint[1], after[0] - waypoint[0])

    return into + math.remainder(out - into, math.tau) / 2


def _ahead(point: Point, heading: float, distance: float) -> Point:
    return point[0] + distance * math.cos(heading), point[1] + distance * math.sin(heading)
