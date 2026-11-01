"""Junction template: where a yard road meets a public road.

One-way curves lead in from each road lane to the junction node and out from it to each lane;
the stem into the yard starts at the junction node. A stem of two one-way lanes has a meeting
point per lane instead, half the lane gap to each side of the stem's centre line. Each curve
leaves or joins its lane tangentially at the yard radius, so it works on straight and curved
roads, with two one-way lanes (as from the AI scan) or one two-way road. Where a curve is
blocked on the drivability map, other places along the lane are tried, then tighter radii down
to MIN_RADIUS, then the route finder; a curve that still does not fit is left out and listed.

Headings are in radians in the x-z plane; as z points south on the map, a rising heading is a
turn to the right.
"""

import math
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from itertools import pairwise

from autodrive_editor.editing.commands.add_route import AddRouteCommand
from autodrive_editor.editing.dubins import Pose, shortest_path
from autodrive_editor.editing.path_shapes import spaced_points
from autodrive_editor.editing.route_finder import Grid, Route, RouteRequest, Vehicle
from autodrive_editor.file_io.navigation_costmap import NavigationCostmap
from autodrive_editor.i18n import tr
from autodrive_editor.model.autodrive_data import AutoDriveData, NodeData
from autodrive_editor.model.connections import (
    CONNECTION_STATES,
    NO_CONNECTION,
    ConnectionType,
    is_reverse_connection,
    read_connection_state,
)

Point = tuple[float, float]

# Turning radius of curves in yards.
YARD_RADIUS = 6.0
# Curves tighten in RADIUS_STEP steps down to MIN_RADIUS where the yard radius does not fit.
MIN_RADIUS = 4.0
RADIUS_STEP = 1.0
# Places where a curve leaves or joins its lane are tried every LEAVE_STEP metres up to
# ALONG_ROAD from the junction, and lanes are followed that far plus the room for a curve.
ALONG_ROAD = 25.0
LEAVE_STEP = 1.0
# An existing lane node this close to such a place is used instead of a new one.
SNAP = 1.0
# The lane in the other direction of a two-lane road lies this close.
OPPOSITE_LANE = 12.0
# A curve turns at most this much more than the angle between lane and stem (no loops).
EXTRA_TURN = math.radians(30)
# Around the junction node and the curve's road end, blocked cells do not count: the junction
# may lie under a roof, and roads run close to fences.
FREE_RADIUS = 3.0
# Curves leave and join a road lane with this kink at the road node, like hand-made forks.
FORK_KINK = math.radians(20)
# Nodes on a curve are at most this many degrees of turn apart.
NODE_TURN = math.radians(22.5)
# Curve points this close to the line behind the junction, on a piece this parallel to it, lie on
# it (curves from road ends 1 m apart reach it a few centimetres beside it), in metres / radians.
STEM_TOLERANCE = 0.1
STEM_PARALLEL = math.radians(2)
# Points checked along a curve, in metres.
SAMPLE = 0.5
# Distance between the two lanes of a two-lane stem.
LANE_GAP = 5.5
# A road across the junction starts or ends at most this far from the junction's foot ...
ACROSS = 80.0
# ... and at most this far to the side of the stem's line, on the far side of the road.
ACROSS_SIDEWAYS = 10.0
# Straight lanes across try these multiples of the yard radius, the gentlest first.
ACROSS_RADII = (8, 4, 2, 1)


class CurveKind(Enum):
    IN = "in"
    OUT = "out"


BOTH = (CurveKind.IN, CurveKind.OUT)


class Stem(Enum):
    """The stem into the yard: matching the road, one two-way road, or two one-way lanes."""

    AUTO = "auto"
    TWO_WAY = "two_way"
    TWO_LANES = "two_lanes"


@dataclass(frozen=True)
class RoadLane:
    """Part of a road lane near the junction: its node IDs and positions in driving order."""

    node_ids: tuple[int, ...]
    points: tuple[Point, ...]


@dataclass(frozen=True)
class RoadEnd:
    """Where a curve leaves or joins its lane: an existing node, or a point on the connection
    from lane node `index` to the next one."""

    point: Point
    node_id: int | None = None
    index: int | None = None


@dataclass(frozen=True)
class Curve:
    kind: CurveKind
    lane: RoadLane
    road_end: RoadEnd
    # From the road end to the junction (IN) or from the junction to the road end (OUT).
    points: tuple[Point, ...]
    radius: float
    # Built by the route finder, not as a Dubins path.
    searched: bool = False
    # A straight lane across the road (see roads_across), not a turn curve.
    across: bool = False


@dataclass
class JunctionPlan:
    curves: list[Curve]
    # The curves that do not fit, as text for the user, and as straight lines between their ends.
    missing: list[str]
    gaps: list[tuple[Point, Point]] = field(default_factory=list)

    def paths(self) -> list[tuple[Point, ...]]:
        """Lines for the preview."""

        return [curve.points for curve in self.curves]


def road_lanes(autodrive_data: AutoDriveData, source_id: int, target_id: int) -> list[RoadLane]:
    """The lanes of the road with the connection: a two-way road gives its lane each way, a
    one-way lane gives itself and the nearest lane the other way within OPPOSITE_LANE, if any."""

    nodes = autodrive_data.nodes
    source, target = nodes[source_id], nodes[target_id]
    lane = _follow(autodrive_data, source_id, target_id)

    if source_id in target.outgoing:
        return [lane, _reversed(lane)]

    foot = ((source.x + target.x) / 2, (source.z + target.z) / 2)
    heading = math.atan2(target.z - source.z, target.x - source.x)
    best = None

    for node in nodes.values():
        if math.hypot(node.x - foot[0], node.z - foot[1]) > OPPOSITE_LANE + 20:
            continue

        for other_id in node.outgoing:
            other = nodes.get(other_id)

            if other is None or {node.node_id, other_id} & set(lane.node_ids):
                continue

            if is_reverse_connection(node, other):
                continue

            other_heading = math.atan2(other.z - node.z, other.x - node.x)

            if math.cos(other_heading - heading) > -0.7:
                continue

            distance = _distance_to_segment(foot, (node.x, node.z), (other.x, other.z))

            if distance <= OPPOSITE_LANE and (best is None or distance < best[0]):
                best = (distance, node.node_id, other_id)

    if best is None:
        return [lane]

    return [lane, _follow(autodrive_data, best[1], best[2])]


def uses_two_lanes(stem: Stem, lanes: list[RoadLane]) -> bool:
    """Whether the stem is two one-way lanes. Auto gives two lanes on a road of two one-way
    lanes, a two-way stem on a two-way road or a single one-way lane."""

    if stem == Stem.AUTO:
        return len(lanes) == 2 and lanes[1].node_ids != lanes[0].node_ids[::-1]

    return stem == Stem.TWO_LANES


def is_on_two_way_road(autodrive_data: AutoDriveData, node_id: int) -> bool:
    """Whether the node has a two-way connection."""

    node = autodrive_data.nodes[node_id]

    return bool(node.outgoing & node.incoming)


def foot_on_lane(lane: RoadLane, point: Point) -> Pose:
    """The lane point closest to `point`, with the lane heading there."""

    best = None

    for a, b in pairwise(lane.points):
        t = _segment_fraction(point, a, b)
        foot = (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]))
        distance = math.dist(point, foot)

        if best is None or distance < best[0]:
            best = (distance, (*foot, _heading(a, b)))

    return best[1]


def stem_poses(junction: Pose, tip: Point, spacing: float) -> list[Pose]:
    """The stem's centre line from the junction to the tip: leaving along the junction's
    heading and bending in one arc to the tip. Poses at most `spacing` and NODE_TURN apart."""

    x, z, heading = junction
    ux, uz = math.cos(heading), math.sin(heading)
    # The tip along the heading and to its right (where a rising heading turns).
    along = (tip[0] - x) * ux + (tip[1] - z) * uz
    side = (tip[1] - z) * ux - (tip[0] - x) * uz
    length = math.hypot(along, side)

    if length < 1e-6:
        return [junction]

    angle = 2 * math.atan2(side, along)
    radius = math.inf

    if abs(side) > 1e-6 * length:
        radius = length * length / (2 * side)
        length = radius * angle

    count = math.ceil(max(length / spacing, abs(angle) / NODE_TURN))
    poses = []

    for step in range(count + 1):
        arc = length * step / count
        turn = 0.0 if math.isinf(radius) else arc / radius
        forward = arc if math.isinf(radius) else radius * math.sin(turn)
        right = 0.0 if math.isinf(radius) else radius * (1 - math.cos(turn))
        poses.append((x + forward * ux - right * uz, z + forward * uz + right * ux, heading + turn))

    poses[-1] = (*tip, poses[-1][2])

    return poses


def roads_across(
    autodrive_data: AutoDriveData, lanes: list[RoadLane], foot: Point, heading: float
) -> list[tuple[CurveKind, RoadLane]]:
    """The road on the far side, opposite a stem leaving `foot` along the heading: where turn
    curves from the road lanes meet (OUT: the lane from that node on) and where turn curves to
    them split (IN: the lane up to that node). Each lies within ACROSS of the foot and
    ACROSS_SIDEWAYS of the line opposite the stem, and needs at least two curves."""

    nodes = autodrive_data.nodes
    on_road = {node_id for lane in lanes for node_id in lane.node_ids}
    ends = {CurveKind.OUT: {}, CurveKind.IN: {}}

    for road_id in on_road:
        node = nodes[road_id]

        for kind, firsts in ((CurveKind.OUT, node.outgoing), (CurveKind.IN, node.incoming)):
            for first_id in firsts - on_road:
                end = _branch_end(nodes, road_id, first_id, kind == CurveKind.OUT, on_road)

                if end is not None:
                    ends[kind].setdefault(end[0], set()).add(end[1])

    result = []

    for kind, found in ends.items():
        best = None

        for end_id, lasts in found.items():
            node = nodes[end_id]
            dx, dz = node.x - foot[0], node.z - foot[1]
            distance = math.hypot(dx, dz)

            if len(lasts) < 2 or not 0 < distance <= ACROSS:
                continue

            opposite = -(dx * math.cos(heading) + dz * math.sin(heading))
            sideways = abs(dx * math.sin(heading) - dz * math.cos(heading))
            onward = (node.outgoing if kind == CurveKind.OUT else node.incoming) - lasts

            if opposite <= 0 or sideways > ACROSS_SIDEWAYS or not onward:
                continue

            if best is None or distance < best[0]:
                best = (distance, end_id, min(onward))

        if best is not None:
            _, end_id, onward_id = best
            node_ids = (end_id, onward_id) if kind == CurveKind.OUT else (onward_id, end_id)
            points = tuple((nodes[i].x, nodes[i].z) for i in node_ids)
            result.append((kind, RoadLane(node_ids, points)))

    return result


def _branch_end(
    nodes: dict, road_id: int, first_id: int, forward: bool, on_road: set[int]
) -> tuple[int, int] | None:
    """Follows a branch from a road node (along its connections if `forward`, against them
    otherwise) to the first node where it meets or splits from others: that node and the one
    before it. None if the branch returns to the road, ends, or leads beyond 2 * ACROSS."""

    start = nodes[road_id]
    previous_id, current_id = road_id, first_id

    while current_id not in on_road:
        current = nodes.get(current_id)

        if current is None or math.hypot(current.x - start.x, current.z - start.z) > 2 * ACROSS:
            return None

        if len(current.outgoing | current.incoming) >= 3:
            return current_id, previous_id

        onward = (current.outgoing if forward else current.incoming) - {previous_id}

        if len(onward) != 1:
            return None

        previous_id, current_id = current_id, next(iter(onward))

    return None


def lane_poses(junction: Pose, gap: float) -> tuple[Pose, Pose]:
    """The meeting points of a two-lane stem: the in-lane half the gap to the right of the way
    into the yard, the out-lane half the gap to the left."""

    x, z, heading = junction
    right_x, right_z = -math.sin(heading) * gap / 2, math.cos(heading) * gap / 2

    return (x + right_x, z + right_z, heading), (x - right_x, z - right_z, heading)


def junction_distance(
    lanes: list[RoadLane], foot: Point, heading: float, radius: float, gap: float = 0.0
) -> float:
    """How far from `foot` along the heading the curves of a junction meet: far enough past each
    lane the line crosses that both the curve in from it and the one out to it fit as an arc of
    the radius, turning the angle φ between lane and stem or its supplement: r (1 + |cos φ|)
    / sin φ past the lane, one radius where the stem leaves the road square. With a lane `gap`,
    far enough for both lanes of the stem (see lane_poses)."""

    if gap > 0:
        return max(
            junction_distance(lanes, pose[:2], heading, radius)
            for pose in lane_poses((*foot, heading), gap)
        )

    dx, dz = math.cos(heading), math.sin(heading)
    distance = radius

    for lane in lanes:
        for (ax, az), (bx, bz) in pairwise(lane.points):
            ex, ez = bx - ax, bz - az
            denominator = dx * ez - dz * ex

            if abs(denominator) < 1e-9:
                continue

            # Crossing at foot + t * direction = a + u * (b - a).
            t = ((ax - foot[0]) * ez - (az - foot[1]) * ex) / denominator
            u = ((ax - foot[0]) * dz - (az - foot[1]) * dx) / denominator

            if 0 <= u <= 1:
                length = math.hypot(ex, ez)
                sine = abs(denominator) / length
                cosine = abs(dx * ex + dz * ez) / length
                distance = max(distance, t + radius * (1 + cosine) / sine)

    return distance


def plan_junction(
    lanes: list[RoadLane],
    junction: Pose,
    kinds: tuple[CurveKind, ...],
    radius: float,
    costmap: NavigationCostmap | None,
    vehicle: Vehicle,
    marker_ids: frozenset[int] = frozenset(),
    find_route: Callable[[RouteRequest], Route | None] | None = None,
    gap: float = 0.0,
    across: list[tuple[CurveKind, RoadLane]] = (),
) -> JunctionPlan:
    """The curves of each kind between each lane and the junction, whose heading points into
    the yard; with a lane `gap`, curves in meet at the in-lane and curves out at the out-lane of
    a two-lane stem. Curves avoid blocked cells (see FREE_RADIUS) and never end on a marker
    node. Straight lanes lead to and from the road `across` (see roads_across)."""

    reach = max((math.dist(junction[:2], lane.points[0]) for _, lane in across), default=0.0)
    checker = _BlockedCheck(costmap, junction, radius, vehicle, reach)
    plan = JunctionPlan([], [])
    in_pose, out_pose = lane_poses(junction, gap) if gap > 0 else (junction, junction)
    poses = {CurveKind.IN: in_pose, CurveKind.OUT: out_pose}

    for kind in kinds:
        pose = poses[kind]

        for lane in lanes:
            curve = _fit(lane, kind, pose, radius, checker, marker_ids)

            if curve is None and find_route is not None:
                curve = _searched(lane, kind, pose, radius, marker_ids, find_route)

            if curve is None:
                plan.missing.append(_missing_text(lane, kind, pose))
                plan.gaps.append((pose[:2], foot_on_lane(lane, pose[:2])[:2]))
            else:
                plan.curves.append(curve)

    for kind, lane in across:
        curve = _straight(lane, kind, poses[kind], radius, checker, find_route)

        if curve is None:
            plan.missing.append(_missing_across_text(lane, kind, junction))
            plan.gaps.append(_across_gap(lane, kind, poses[kind]))
        else:
            plan.curves.append(curve)

    return plan


def _across_gap(lane: RoadLane, kind: CurveKind, pose: Pose) -> tuple[Point, Point]:
    """Straight line for a missing lane across: from the stem lane to the road's end."""

    return pose[:2], lane.points[0 if kind == CurveKind.OUT else -1]


def _straight(
    lane: RoadLane,
    kind: CurveKind,
    pose: Pose,
    radius: float,
    checker: "_BlockedCheck",
    find_route: Callable[[RouteRequest], Route | None] | None,
) -> Curve | None:
    """The straight lane between the stem lane at `pose` and the end of a road across: the
    gentlest clear Dubins path of the ACROSS_RADII, else one from the route finder."""

    index = 0 if kind == CurveKind.OUT else -1
    end = RoadEnd(lane.points[index], node_id=lane.node_ids[index])
    heading = _heading(*lane.points)

    for factor in ACROSS_RADII:
        path = _curve_path(kind, end.point, heading, pose, radius * factor)

        if path is None:
            continue

        points = [sample[:2] for sample in path.sample(SAMPLE)]

        if checker.is_clear(points, (pose[:2], end.point)):
            if kind == CurveKind.IN:
                points[0], points[-1] = end.point, pose[:2]
            else:
                points[0], points[-1] = pose[:2], end.point

            return Curve(kind, lane, end, tuple(points), radius * factor, across=True)

    if find_route is None:
        return None

    if kind == CurveKind.IN:
        request = RouteRequest((end.point, pose[:2]), (heading,), (pose[2],), turning_radius=radius)
    else:
        request = RouteRequest(
            (pose[:2], end.point), (pose[2] + math.pi,), (heading,), turning_radius=radius
        )

    route = find_route(request)

    if route is None or not route.is_clear:
        return None

    return Curve(kind, lane, end, tuple(route.points), radius, searched=True, across=True)


def junction_command(
    autodrive_data: AutoDriveData,
    plan: JunctionPlan,
    junction: Pose,
    spacing: float,
    height_for_new_node: Callable[[AutoDriveData, float, float], float],
    junction_id: int | None = None,
    stem: list[Pose] = (),
    gap: float = 0.0,
    tip_id: int | None = None,
) -> AddRouteCommand:
    """The edit that adds the curves: a new junction node unless `junction_id` is given, new
    nodes along each curve, and the lane connections split where a curve leaves or joins one.
    Curve ends on the same connection closer than SNAP share a node. Curves that end along the
    line behind the junction share its nodes from where they reach it; a piece used both in and
    out is two-way. A two-way stem follows the `stem` poses (see stem_poses) from the junction.
    With a lane `gap`, each lane of the stem gets its own meeting node and runs one-way beside
    the stem poses (`junction_id` is not used then). Both lanes, or the two-way stem, end at
    the node `tip_id` if given."""

    next_id = max(autodrive_data.nodes, default=0) + 1
    new_nodes: list[NodeData] = []

    def new_node(point: Point) -> int:
        nonlocal next_id
        y = height_for_new_node(autodrive_data, *point)
        new_nodes.append(NodeData(next_id, point[0], y, point[1]))
        next_id += 1

        return next_id - 1

    regular = CONNECTION_STATES[ConnectionType.REGULAR]
    # New nodes on lane connections, per connection (source, target): (fraction, point, id).
    splits: dict[tuple[int, int], list[tuple[float, Point, int]]] = {}
    connections = []

    def stem_line(lane_index: int | None, meeting_id: int) -> list[int]:
        return _stem_ids(stem, lane_index, gap, meeting_id, tip_id, new_node)

    if gap > 0:
        for index, (kind, pose) in enumerate(zip(BOTH, lane_poses(junction, gap), strict=True)):
            meeting_id = new_node(pose[:2])
            curves = [curve for curve in plan.curves if curve.kind == kind]
            connections += _curve_connections(curves, pose, meeting_id, spacing, splits, new_node)
            stem_ids = stem_line(index, meeting_id)

            if kind == CurveKind.OUT:
                stem_ids.reverse()

            connections += [(a, b, regular) for a, b in pairwise(stem_ids)]
    else:
        if junction_id is None:
            junction_id = new_node(junction[:2])

        connections += _curve_connections(
            plan.curves, junction, junction_id, spacing, splits, new_node
        )
        dual = CONNECTION_STATES[ConnectionType.DUAL]
        connections += [(a, b, dual) for a, b in pairwise(stem_line(None, junction_id))]

    for (source_id, target_id), points in splits.items():
        state = read_connection_state(autodrive_data, source_id, target_id)
        chain = [source_id, *(node_id for _, _, node_id in sorted(points)), target_id]
        connections.append((source_id, target_id, NO_CONNECTION))
        connections += [(a, b, state) for a, b in pairwise(chain)]

    return AddRouteCommand(tr("Junction"), autodrive_data, new_nodes, connections)


def _stem_ids(
    stem: list[Pose],
    lane_index: int | None,
    gap: float,
    meeting_id: int,
    tip_id: int | None,
    new_node: Callable[[Point], int],
) -> list[int]:
    """Node IDs along the stem (lane_index None) or one of its lanes (see lane_poses), from the
    meeting node to the tip, or to the node `tip_id` if given."""

    points = [
        pose[:2] if lane_index is None else lane_poses(pose, gap)[lane_index][:2]
        for pose in stem[1:]
    ]

    if tip_id is not None:
        return [meeting_id, *(new_node(point) for point in points[:-1]), tip_id]

    return [meeting_id, *(new_node(point) for point in points)]


def _curve_connections(
    curves: list[Curve],
    junction: Pose,
    junction_id: int,
    spacing: float,
    splits: dict,
    new_node: Callable[[Point], int],
) -> list:
    """Connections of the curves meeting at the junction node, with new nodes along them and on
    the line behind the junction (see junction_command)."""

    regular = CONNECTION_STATES[ConnectionType.REGULAR]
    # Per curve: its own points from the road to the stem line, and where it reaches the line.
    parts = [_stem_part(curve, junction) for curve in curves]
    stem = _stem_nodes(junction, parts, spacing, new_node, junction_id)
    connections = []

    for curve, (points, back) in zip(curves, parts, strict=True):
        road_id = _road_end_id(curve, splits, new_node)
        spaced = spaced_points(points, min(spacing, curve.radius * NODE_TURN))
        chain = [road_id, *(new_node(point) for point in spaced[1:-1]), stem[back]]

        if curve.kind == CurveKind.OUT:
            chain.reverse()

        connections += [(a, b, regular) for a, b in pairwise(chain)]

    return connections + _stem_connections(curves, parts, stem)


def _stem_part(curve: Curve, junction: Pose) -> tuple[list[Point], float]:
    """The curve's points from the road to where it reaches the line behind the junction (along
    its heading, towards the road), and the distance of that point from the junction, rounded
    to SNAP. Curves that do not end along that line reach it at the junction."""

    points = list(curve.points if curve.kind == CurveKind.IN else reversed(curve.points))
    x, z, heading = junction
    dx, dz = math.cos(heading), math.sin(heading)
    index = len(points) - 1

    while index > 0:
        px, pz = points[index - 1]
        back = (x - px) * dx + (z - pz) * dz
        qx, qz = points[index]
        length = math.hypot(qx - px, qz - pz)
        sideways = abs((qx - px) * dz - (qz - pz) * dx)

        if abs((px - x) * dz - (pz - z) * dx) > STEM_TOLERANCE or back < -1e-6:
            break
        # The last point was moved onto the junction, so the last piece is left out.
        parallel = index == len(points) - 1 or sideways <= length * math.sin(STEM_PARALLEL)

        if not parallel:
            break

        index -= 1

    back = SNAP * round(((x - points[index][0]) * dx + (z - points[index][1]) * dz) / SNAP)

    if back <= 0 or index == 0:
        return points, 0.0

    return [*points[:index], (x - back * dx, z - back * dz)], back


def _stem_nodes(
    junction: Pose,
    parts: list[tuple[list[Point], float]],
    spacing: float,
    new_node: Callable[[Point], int],
    junction_id: int,
) -> dict[float, int]:
    """Node IDs on the line behind the junction by distance from it: the junction, a node where
    each curve reaches the line, and nodes between them at most `spacing` apart."""

    x, z, heading = junction
    dx, dz = math.cos(heading), math.sin(heading)
    distances = sorted({back for _, back in parts} | {0.0})
    stem = {0.0: junction_id}

    for near, far in pairwise(distances):
        count = math.ceil((far - near) / spacing)

        for step in range(1, count + 1):
            back = far if step == count else near + (far - near) * step / count
            stem[back] = new_node((x - back * dx, z - back * dz))

    return stem


def _stem_connections(
    curves: list[Curve], parts: list[tuple[list[Point], float]], stem: dict[float, int]
) -> list:
    """Connections along the line behind the junction: towards it where curves in use them,
    away from it where curves out do, two-way where both do."""

    connections = []

    for near, far in pairwise(sorted(stem)):
        used_in = any(
            curve.kind == CurveKind.IN and back >= far
            for curve, (_, back) in zip(curves, parts, strict=True)
        )
        used_out = any(
            curve.kind == CurveKind.OUT and back >= far
            for curve, (_, back) in zip(curves, parts, strict=True)
        )
        if used_in and used_out:
            connections.append((stem[far], stem[near], CONNECTION_STATES[ConnectionType.DUAL]))
        elif used_in:
            connections.append((stem[far], stem[near], CONNECTION_STATES[ConnectionType.REGULAR]))
        elif used_out:
            connections.append((stem[near], stem[far], CONNECTION_STATES[ConnectionType.REGULAR]))

    return connections


def _road_end_id(curve: Curve, splits: dict, new_node: Callable[[Point], int]) -> int:
    end = curve.road_end

    if end.node_id is not None:
        return end.node_id

    source_id, target_id = curve.lane.node_ids[end.index], curve.lane.node_ids[end.index + 1]
    key = (source_id, target_id)

    if key not in splits and (target_id, source_id) in splits:
        key = (target_id, source_id)

    points = splits.setdefault(key, [])

    for _, point, node_id in points:
        if math.dist(point, end.point) < SNAP:
            return node_id

    a, b = curve.lane.points[end.index], curve.lane.points[end.index + 1]

    if key != (source_id, target_id):
        a, b = b, a

    fraction = math.dist(a, end.point) / max(math.dist(a, b), 1e-9)
    node_id = new_node(end.point)
    points.append((fraction, end.point, node_id))

    return node_id


def _fit(
    lane: RoadLane,
    kind: CurveKind,
    junction: Pose,
    radius: float,
    checker: "_BlockedCheck",
    marker_ids: frozenset[int],
) -> Curve | None:
    """The shortest clear Dubins curve between the lane and the junction, at the largest radius
    from `radius` down to MIN_RADIUS that has one."""

    places = _places(lane, junction, marker_ids)
    current = radius

    while current >= MIN_RADIUS - 1e-9:
        paths = []

        for end, heading in places:
            path = _curve_path(kind, end.point, heading, junction, current)

            if path is not None:
                paths.append((path.length, end, path))

        for _, end, path in sorted(paths, key=lambda item: item[0]):
            points = [pose[:2] for pose in path.sample(SAMPLE)]

            if checker.is_clear(points, (junction[:2], end.point)):
                if kind == CurveKind.IN:
                    points[0], points[-1] = end.point, junction[:2]
                else:
                    points[0], points[-1] = junction[:2], end.point

                return Curve(kind, lane, end, tuple(points), current)

        current -= RADIUS_STEP

    return None


def _curve_path(kind: CurveKind, point: Point, lane_heading: float, junction: Pose, radius: float):
    """The Dubins path of the curve, or None if it turns much more than needed (a loop)."""

    lane_heading = kinked(kind, point, lane_heading, junction[:2])

    if kind == CurveKind.IN:
        start, goal = (*point, lane_heading), junction
    else:
        start, goal = (junction[0], junction[1], junction[2] + math.pi), (*point, lane_heading)

    path = shortest_path(start, goal, radius)

    if path is None:
        return None

    return path if _turns_little(path, start[2], goal[2], radius) else None


def _turns_little(path, start_heading: float, goal_heading: float, radius: float) -> bool:
    """Whether the Dubins path turns at most EXTRA_TURN more than needed (no loop)."""

    needed = abs(math.remainder(goal_heading - start_heading, math.tau))
    turned = sum(
        length for letter, length in zip(path.word, path.lengths, strict=True) if letter != "S"
    )

    return turned / radius <= needed + EXTRA_TURN


def _places(
    lane: RoadLane, junction: Pose, marker_ids: frozenset[int]
) -> list[tuple[RoadEnd, float]]:
    """Places along the lane within ALONG_ROAD of the junction's foot, every LEAVE_STEP metres,
    each with the lane heading there. A place within SNAP of a lane node becomes that node,
    unless it carries a marker or starts or ends the lane part."""

    lengths = [0.0]

    for a, b in pairwise(lane.points):
        lengths.append(lengths[-1] + math.dist(a, b))

    foot = _arc_length(lane, junction[:2], lengths)
    places = []
    seen_nodes = set()
    count = math.floor(ALONG_ROAD / LEAVE_STEP)

    for step in range(-count, count + 1):
        along = foot + step * LEAVE_STEP

        if not 0 < along < lengths[-1]:
            continue

        index = max(i for i in range(len(lengths) - 1) if lengths[i] <= along)
        snapped = None

        for node_index in (index, index + 1):
            node_id = lane.node_ids[node_index]

            if (
                0 < node_index < len(lane.node_ids) - 1
                and abs(lengths[node_index] - along) < SNAP
                and node_id not in marker_ids
            ):
                snapped = node_index

        if snapped is not None:
            if snapped in seen_nodes:
                continue

            seen_nodes.add(snapped)
            point = lane.points[snapped]
            before = _heading(lane.points[snapped - 1], point)
            after = _heading(point, lane.points[snapped + 1])
            heading = before + math.remainder(after - before, math.tau) / 2
            places.append((RoadEnd(point, node_id=lane.node_ids[snapped]), heading))
            continue

        a, b = lane.points[index], lane.points[index + 1]
        fraction = (along - lengths[index]) / max(lengths[index + 1] - lengths[index], 1e-9)
        point = (a[0] + fraction * (b[0] - a[0]), a[1] + fraction * (b[1] - a[1]))
        places.append((RoadEnd(point, index=index), _heading(a, b)))

    return places


def _searched(
    lane: RoadLane,
    kind: CurveKind,
    junction: Pose,
    radius: float,
    marker_ids: frozenset[int],
    find_route: Callable[[RouteRequest], Route | None],
) -> Curve | None:
    """The curve built by the route finder from the place on the lane where the shortest Dubins
    curve would leave or join it."""

    best = None

    for end, heading in _places(lane, junction, marker_ids):
        path = _curve_path(kind, end.point, heading, junction, radius)

        if path is not None and (best is None or path.length < best[0]):
            best = (path.length, end, heading)

    if best is None:
        return None

    _, end, heading = best
    heading = kinked(kind, end.point, heading, junction[:2])

    if kind == CurveKind.IN:
        request = RouteRequest(
            (end.point, junction[:2]), (heading,), (junction[2],), turning_radius=radius
        )
    else:
        request = RouteRequest(
            (junction[:2], end.point), (junction[2] + math.pi,), (heading,), turning_radius=radius
        )

    route = find_route(request)

    if route is None or not route.is_clear:
        return None

    return Curve(kind, lane, end, tuple(route.points), radius, searched=True)


def _missing_text(lane: RoadLane, kind: CurveKind, junction: Pose) -> str:
    """E.g. "No left turn in from the north"."""

    lane_heading = _heading(lane.points[0], lane.points[-1])

    if kind == CurveKind.IN:
        turn = math.remainder(junction[2] - lane_heading, math.tau)
        direction = _compass(lane_heading + math.pi)
        text = (
            tr("No right turn in from the {direction}")
            if turn > 0
            else tr("No left turn in from the {direction}")
        )
    else:
        turn = math.remainder(lane_heading - junction[2] - math.pi, math.tau)
        direction = _compass(lane_heading)
        text = (
            tr("No right turn out to the {direction}")
            if turn > 0
            else tr("No left turn out to the {direction}")
        )

    return text.format(direction=direction)


def _missing_across_text(lane: RoadLane, kind: CurveKind, junction: Pose) -> str:
    """E.g. "No straight on to the north"."""

    point = lane.points[0 if kind == CurveKind.OUT else -1]
    direction = _compass(_heading(junction[:2], point))

    if kind == CurveKind.OUT:
        return tr("No straight on to the {direction}").format(direction=direction)

    return tr("No straight on from the {direction}").format(direction=direction)


def _compass(heading: float) -> str:
    """The compass direction of the heading on the map (x east, z south)."""

    names = (tr("east"), tr("south"), tr("west"), tr("north"))

    return names[round(heading / (math.pi / 2)) % 4]


class _BlockedCheck:
    """Whether curve points stay off blocked cells and their safety distance."""

    def __init__(
        self,
        costmap: NavigationCostmap | None,
        junction: Pose,
        radius: float,
        vehicle: Vehicle,
        reach: float = 0.0,
    ):
        """Covers the curves around the junction and points up to `reach` from it."""

        self.junction = junction[:2]
        self.grid = None

        if costmap is None:
            return

        margin = max(ALONG_ROAD + 3 * radius + OPPOSITE_LANE, reach + 3 * radius)
        half_width, half_height = costmap.width / 2, costmap.height / 2
        x, z = self.junction
        bounds = (
            max(0, math.floor(x - margin + half_width)),
            max(0, math.floor(z - margin + half_height)),
            min(costmap.width, math.ceil(x + margin + half_width)),
            min(costmap.height, math.ceil(z + margin + half_height)),
        )
        self.grid = Grid(costmap, bounds, vehicle.width / 2 + vehicle.margin)

    def is_clear(self, points: list[Point], free_points: tuple[Point, ...]) -> bool:
        """Whether the points stay clear, apart from those within FREE_RADIUS of the free points
        (the curve's meeting point and road end)."""

        if self.grid is None:
            return True

        for point in points:
            if any(math.dist(point, free) <= FREE_RADIUS for free in free_points):
                continue

            index = self.grid.index(*point)

            if index is None or self.grid.blocked[index]:
                return False

        return True


def _follow(autodrive_data: AutoDriveData, source_id: int, target_id: int) -> RoadLane:
    """The lane through the connection, followed both ways while it goes on about straight,
    until ALONG_ROAD plus room for a curve beyond the connection."""

    nodes = autodrive_data.nodes
    reach = ALONG_ROAD + 4 * MIN_RADIUS + 20
    ahead = _walk(nodes, source_id, target_id, reach, forward=True)
    behind = _walk(nodes, target_id, source_id, reach, forward=False)
    node_ids = [*reversed(behind), source_id, target_id, *ahead]

    return RoadLane(tuple(node_ids), tuple((nodes[i].x, nodes[i].z) for i in node_ids))


def _walk(nodes: dict, previous_id: int, current_id: int, reach: float, forward: bool) -> list[int]:
    """Node IDs after `current_id` going on from `previous_id` along driving connections (forward)
    or against them, the straightest way at forks, until `reach` metres."""

    walked = 0.0
    result = []
    seen = {previous_id, current_id}

    while walked < reach:
        previous, current = nodes[previous_id], nodes[current_id]
        heading = math.atan2(current.z - previous.z, current.x - previous.x)
        candidates = current.outgoing if forward else current.incoming
        best = None

        for other_id in candidates:
            other = nodes.get(other_id)

            if other is None or other_id in seen:
                continue

            # Driven connections only, not reverse ones.
            if current_id not in (other.incoming if forward else other.outgoing):
                continue

            turn = abs(
                math.remainder(
                    math.atan2(other.z - current.z, other.x - current.x) - heading, math.tau
                )
            )

            if turn < math.radians(60) and (best is None or turn < best[0]):
                best = (turn, other_id)

        if best is None:
            break

        walked += math.dist((current.x, current.z), (nodes[best[1]].x, nodes[best[1]].z))
        previous_id, current_id = current_id, best[1]
        seen.add(current_id)
        result.append(current_id)

    return result


def _reversed(lane: RoadLane) -> RoadLane:
    return RoadLane(lane.node_ids[::-1], lane.points[::-1])


def _arc_length(lane: RoadLane, point: Point, lengths: list[float]) -> float:
    """Distance along the lane to the lane point closest to `point`."""

    best = None

    for index, (a, b) in enumerate(pairwise(lane.points)):
        t = _segment_fraction(point, a, b)
        foot = (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]))
        distance = math.dist(point, foot)

        if best is None or distance < best[0]:
            best = (distance, lengths[index] + t * (lengths[index + 1] - lengths[index]))

    return best[1]


def _segment_fraction(point: Point, a: Point, b: Point) -> float:
    abx, abz = b[0] - a[0], b[1] - a[1]
    length_squared = abx * abx + abz * abz

    if length_squared == 0:
        return 0.0

    return min(max(((point[0] - a[0]) * abx + (point[1] - a[1]) * abz) / length_squared, 0.0), 1.0)


def _distance_to_segment(point: Point, a: Point, b: Point) -> float:
    t = _segment_fraction(point, a, b)

    return math.dist(point, (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])))


def kinked(kind: CurveKind, point: Point, lane_heading: float, toward: Point) -> float:
    """The heading of a curve where it leaves (IN) or joins (OUT) a lane at the point: the lane
    heading turned by FORK_KINK to the side where `toward` lies."""

    dx, dz = math.cos(lane_heading), math.sin(lane_heading)
    cross = dx * (toward[1] - point[1]) - dz * (toward[0] - point[0])
    side = math.copysign(1.0, cross) if abs(cross) > 1e-9 else 0.0

    return lane_heading + side * FORK_KINK * (1 if kind == CurveKind.IN else -1)


def _heading(a: Point, b: Point) -> float:
    return math.atan2(b[1] - a[1], b[0] - a[0])
