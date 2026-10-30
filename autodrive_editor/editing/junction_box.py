"""Junction box in the NF Marsch style, where a stem of two one-way lanes meets a road of two
one-way lanes. Both stem lanes run across both road lanes and share a node where they cross; a
centre node with two-way diagonals to the four crossing nodes carries left turns and U-turns;
right turns are arcs from box edge to box edge. The lane pieces from a crossing node out to the
box edge are two-way, those between the crossings keep their direction: AutoDrive's traffic check
looks ahead over two-way pieces and lets a driver on one go first, so drivers wait at the edge
while another one is in the box. A half box (yard entrance) has no arm on the far side; a road
across (see roads_across) gets that arm, as straight lanes from the far box edge.

Headings as in junction.py: radians in the x-z plane, a rising heading turns right.
"""

import math
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from itertools import pairwise

from autodrive_editor.editing.commands.add_route import AddRouteCommand
from autodrive_editor.editing.dubins import Pose, shortest_path
from autodrive_editor.editing.junction import (
    MIN_RADIUS,
    NODE_TURN,
    RADIUS_STEP,
    SAMPLE,
    SNAP,
    YARD_RADIUS,
    Curve,
    CurveKind,
    RoadEnd,
    RoadLane,
    _BlockedCheck,
    _compass,
    _heading,
    _missing_across_text,
    _stem_ids,
    _straight,
    _turns_little,
    lane_poses,
)
from autodrive_editor.editing.path_shapes import spaced_points
from autodrive_editor.editing.route_finder import Route, RouteRequest, Vehicle
from autodrive_editor.file_io.navigation_costmap import NavigationCostmap
from autodrive_editor.i18n import tr
from autodrive_editor.model.autodrive_data import AutoDriveData, NodeData
from autodrive_editor.model.connections import (
    CONNECTION_STATES,
    NO_CONNECTION,
    ConnectionType,
    read_connection_state,
)

Point = tuple[float, float]

# From the outer lane to the box edge, in metres; also the radius of the right turns.
BOX_MARGIN = 7.0


class Style(Enum):
    """How the Junction task builds a junction: a box, or turn curves (junction.py)."""

    BOX = "box"
    CURVES = "curves"


@dataclass(frozen=True)
class BoxLane:
    """A road lane through the box: box edge, crossing, crossing, box edge in driving order,
    with their distances along the lane."""

    lane: RoadLane
    ends: tuple[RoadEnd, RoadEnd, RoadEnd, RoadEnd]
    along: tuple[float, float, float, float]


@dataclass
class BoxPlan:
    # Where the stem starts: the near box edge on the stem's centre line, heading into the yard.
    junction: Pose
    centre: Point
    crossings: list[Point]
    road: list[BoxLane]
    # The stem's in-lane and out-lane in the box, in driving order: from the far edge (if the
    # box has a far arm) or the far crossing to the near edge, and back.
    stem: list[list[Point]]
    # Right turns and the far arm's straight lanes.
    curves: list[Curve]
    # Pieces that do not fit, and pieces built on blocked ground, as text for the user.
    missing: list[str]
    blocked: list[str]

    def paths(self) -> list[tuple[Point, ...]]:
        """Lines for the preview."""

        lines = [tuple(end.point for end in lane.ends) for lane in self.road]
        lines += [tuple(points) for points in self.stem]
        lines += [(self.centre, crossing) for crossing in self.crossings]

        return lines + [curve.points for curve in self.curves]


def plan_box(
    lanes: list[RoadLane],
    foot: Point,
    heading: float,
    gap: float,
    costmap: NavigationCostmap | None = None,
    vehicle: Vehicle | None = None,
    marker_ids: frozenset[int] = frozenset(),
    across: list[tuple[CurveKind, RoadLane]] = (),
    find_route: Callable[[RouteRequest], Route | None] | None = None,
) -> BoxPlan | None:
    """The box where a stem of two lanes `gap` apart leaves `foot` along the heading. None
    unless the road has two one-way lanes that both stem lanes cross with room for the box."""

    if len(lanes) != 2 or lanes[1].node_ids == lanes[0].node_ids[::-1] or gap <= 0:
        return None

    dx, dz = math.cos(heading), math.sin(heading)
    origins = [pose[:2] for pose in lane_poses((*foot, heading), gap)]
    # (road lane, stem lane): distance along the stem and along the road lane.
    hits = {}

    for road_index, lane in enumerate(lanes):
        for stem_index, origin in enumerate(origins):
            hit = _crossing(lane, origin, heading)

            if hit is None:
                return None

            hits[road_index, stem_index] = hit

    near = max((0, 1), key=lambda index: hits[index, 0][0] + hits[index, 1][0])
    far = 1 - near
    near_t = max(hits[near, 0][0], hits[near, 1][0]) + BOX_MARGIN
    far_t = min(hits[far, 0][0], hits[far, 1][0]) - BOX_MARGIN
    junction = (foot[0] + near_t * dx, foot[1] + near_t * dz, heading)
    near_edges = [pose[:2] for pose in lane_poses(junction, gap)]
    far_edges = [
        pose[:2] for pose in lane_poses((foot[0] + far_t * dx, foot[1] + far_t * dz, heading), gap)
    ]

    road = []
    # (road lane, stem lane): the crossing point.
    crossings = {}

    for road_index, lane in enumerate(lanes):
        box_lane = _box_lane(lane, hits[road_index, 0][1], hits[road_index, 1][1], marker_ids)

        if box_lane is None:
            return None

        first = 0 if hits[road_index, 0][1] < hits[road_index, 1][1] else 1
        crossings[road_index, first] = box_lane.ends[1].point
        crossings[road_index, 1 - first] = box_lane.ends[2].point
        road.append(box_lane)

    reach = max((math.dist(junction[:2], lane.points[0]) for _, lane in across), default=0.0)
    checker = _BlockedCheck(costmap, junction, BOX_MARGIN, vehicle, reach)
    centre = tuple(sum(point[i] for point in crossings.values()) / 4 for i in (0, 1))
    plan = BoxPlan(junction, centre, list(crossings.values()), road, [], [], [], [])
    in_lane = [crossings[far, 0], crossings[near, 0], near_edges[0]]
    out_lane = [near_edges[1], crossings[near, 1], crossings[far, 1]]
    far_arm = {}

    for kind, lane in across:
        index = 0 if kind == CurveKind.IN else 1
        curve = _straight(
            lane, kind, (*far_edges[index], heading), YARD_RADIUS, checker, find_route
        )

        if curve is None:
            plan.missing.append(_missing_across_text(lane, kind, junction))
        else:
            far_arm[kind] = curve

    if CurveKind.IN in far_arm:
        in_lane.insert(0, far_edges[0])
    if CurveKind.OUT in far_arm:
        out_lane.append(far_edges[1])

    plan.stem = [in_lane, out_lane]

    if any(not checker.is_clear(_sampled(line), ()) for line in plan.paths()):
        plan.blocked.append(tr("box"))

    near_lane, far_lane = road[near], road[far]
    turns = [
        (CurveKind.IN, near_lane, _edge_pose(near_lane, 0), (*near_edges[0], heading)),
        (CurveKind.OUT, near_lane, (*near_edges[1], heading + math.pi), _edge_pose(near_lane, 3)),
    ]

    if CurveKind.OUT in far_arm:
        far_out = (*far_edges[1], heading + math.pi)
        turns.append((CurveKind.IN, far_lane, _edge_pose(far_lane, 0), far_out))
    if CurveKind.IN in far_arm:
        turns.append((CurveKind.OUT, far_lane, (*far_edges[0], heading), _edge_pose(far_lane, 3)))

    for kind, box_lane, start, goal in turns:
        name = tr("right turn from the {source} to the {target}").format(
            source=_compass(start[2] + math.pi), target=_compass(goal[2])
        )
        curve = _right_turn(kind, box_lane, start, goal)

        if curve is None:
            plan.missing.append(tr("No {turn}").format(turn=name))
            continue

        plan.curves.append(curve)

        if not checker.is_clear(_sampled(curve.points), (start[:2], goal[:2])):
            plan.blocked.append(name)

    plan.curves += far_arm.values()

    return plan


def box_command(
    autodrive_data: AutoDriveData,
    plan: BoxPlan,
    spacing: float,
    height_for_new_node: Callable[[AutoDriveData, float, float], float],
    stem: list[Pose] = (),
    gap: float = 0.0,
    tip_id: int | None = None,
) -> AddRouteCommand:
    """The edit that builds the box: its nodes, the road lanes split at its edges and
    crossings, the stem lanes from the near edge along the `stem` poses (see stem_poses), to
    the node `tip_id` if given."""

    next_id = max(autodrive_data.nodes, default=0) + 1
    new_nodes: list[NodeData] = []
    ids: dict[Point, int] = {}

    def new_node(point: Point) -> int:
        nonlocal next_id
        y = height_for_new_node(autodrive_data, *point)
        new_nodes.append(NodeData(next_id, point[0], y, point[1]))
        next_id += 1

        return next_id - 1

    def node(point: Point, node_id: int | None = None) -> int:
        if point not in ids:
            ids[point] = node_id if node_id is not None else new_node(point)

        return ids[point]

    regular = CONNECTION_STATES[ConnectionType.REGULAR]
    dual = CONNECTION_STATES[ConnectionType.DUAL]
    crossings = set(plan.crossings)
    connections = []

    for box_lane in plan.road:
        connections += _lane_connections(autodrive_data, box_lane, node)

    for index, points in enumerate(plan.stem):
        for a, b in pairwise(points):
            state = regular if a in crossings and b in crossings else dual
            spaced = spaced_points([a, b], spacing)
            chain = [node(a), *(new_node(point) for point in spaced[1:-1]), node(b)]
            connections += [(source, target, state) for source, target in pairwise(chain)]

        near_edge = points[-1] if index == 0 else points[0]
        stem_ids = _stem_ids(stem, index, gap, node(near_edge), tip_id, new_node)

        if index == 1:
            stem_ids.reverse()

        connections += [(a, b, regular) for a, b in pairwise(stem_ids)]

    connections += [(node(plan.centre), node(crossing), dual) for crossing in plan.crossings]

    for curve in plan.curves:
        end = curve.road_end
        first, last = curve.points[0], curve.points[-1]
        first_id = node(first, end.node_id if curve.kind == CurveKind.IN else None)
        last_id = node(last, end.node_id if curve.kind == CurveKind.OUT else None)
        spaced = spaced_points(list(curve.points), min(spacing, curve.radius * NODE_TURN))
        chain = [first_id, *(new_node(point) for point in spaced[1:-1]), last_id]
        connections += [(a, b, regular) for a, b in pairwise(chain)]

    return AddRouteCommand(tr("Junction"), autodrive_data, new_nodes, connections)


def _lane_connections(
    autodrive_data: AutoDriveData, box_lane: BoxLane, node: Callable[..., int]
) -> list:
    """The road lane through the box: its old connections between the box edges replaced by
    a chain through the box nodes and the lane nodes between them, two-way from each crossing
    out to the edge."""

    lane, along = box_lane.lane, box_lane.along
    lengths = _lengths(lane)
    end_ids = [node(end.point, end.node_id) for end in box_lane.ends]
    chain = sorted(
        [*zip(along, end_ids, strict=True)]
        + [
            (length, node_id)
            for length, node_id in zip(lengths, lane.node_ids, strict=True)
            if along[0] < length < along[3] and node_id not in end_ids
        ]
    )
    removed = [
        (a, b)
        for (a, b), (start, stop) in zip(pairwise(lane.node_ids), pairwise(lengths), strict=True)
        if start < along[3] and stop > along[0]
    ]
    state = read_connection_state(autodrive_data, *removed[0])

    if box_lane.ends[0].node_id is None:
        chain.insert(0, (-math.inf, removed[0][0]))
    if box_lane.ends[3].node_id is None:
        chain.append((math.inf, removed[-1][1]))

    connections = [(a, b, NO_CONNECTION) for a, b in removed]
    dual = CONNECTION_STATES[ConnectionType.DUAL]

    for (start, a), (stop, b) in pairwise(chain):
        inside = along[0] <= start and stop <= along[3]
        between = along[1] <= start and stop <= along[2]
        connections.append((a, b, dual if inside and not between else state))

    return connections


def _box_lane(
    lane: RoadLane, first: float, second: float, marker_ids: frozenset[int]
) -> BoxLane | None:
    """The box points on the lane around its crossings at distances `first` and `second` along
    it; None if the lane part is too short. A point within SNAP of a lane node is that node."""

    lengths = _lengths(lane)
    low, high = sorted((first, second))
    wanted = (low - BOX_MARGIN, low, high, high + BOX_MARGIN)

    if wanted[0] <= 0 or wanted[3] >= lengths[-1]:
        return None

    ends, along, used = [], [], set()

    for distance in wanted:
        index = max(i for i in range(len(lengths) - 1) if lengths[i] <= distance)
        snapped = None

        for node_index in (index, index + 1):
            node_id = lane.node_ids[node_index]

            if (
                0 < node_index < len(lane.node_ids) - 1
                and abs(lengths[node_index] - distance) < SNAP
                and node_id not in marker_ids
                and node_id not in used
            ):
                snapped = node_index

        if snapped is not None:
            used.add(lane.node_ids[snapped])
            ends.append(RoadEnd(lane.points[snapped], node_id=lane.node_ids[snapped]))
            along.append(lengths[snapped])
            continue

        a, b = lane.points[index], lane.points[index + 1]
        fraction = (distance - lengths[index]) / max(lengths[index + 1] - lengths[index], 1e-9)
        point = (a[0] + fraction * (b[0] - a[0]), a[1] + fraction * (b[1] - a[1]))
        ends.append(RoadEnd(point, index=index))
        along.append(distance)

    return BoxLane(lane, tuple(ends), tuple(along))


def _edge_pose(box_lane: BoxLane, end_index: int) -> Pose:
    """A box edge on the lane with the lane heading there."""

    lane, distance = box_lane.lane, box_lane.along[end_index]
    lengths = _lengths(lane)
    index = max(i for i in range(len(lengths) - 1) if lengths[i] <= distance)
    index = min(index, len(lane.points) - 2)

    return (*box_lane.ends[end_index].point, _heading(lane.points[index], lane.points[index + 1]))


def _right_turn(kind: CurveKind, box_lane: BoxLane, start: Pose, goal: Pose) -> Curve | None:
    """The arc of a right turn between the box edges, at BOX_MARGIN or tighter down to
    MIN_RADIUS."""

    radius = BOX_MARGIN

    while radius >= MIN_RADIUS - 1e-9:
        path = shortest_path(start, goal, radius)

        if path is not None and _turns_little(path, start[2], goal[2], radius):
            points = [pose[:2] for pose in path.sample(SAMPLE)]
            points[0], points[-1] = start[:2], goal[:2]
            end = box_lane.ends[0 if kind == CurveKind.IN else 3]

            return Curve(kind, box_lane.lane, end, tuple(points), radius)

        radius -= RADIUS_STEP

    return None


def _crossing(lane: RoadLane, origin: Point, heading: float) -> tuple[float, float] | None:
    """Where the line from `origin` along the heading crosses the lane: the distance along the
    line and along the lane. The crossing closest to the origin."""

    dx, dz = math.cos(heading), math.sin(heading)
    lengths = _lengths(lane)
    best = None

    for index, ((ax, az), (bx, bz)) in enumerate(pairwise(lane.points)):
        ex, ez = bx - ax, bz - az
        denominator = dx * ez - dz * ex

        if abs(denominator) < 1e-9:
            continue

        t = ((ax - origin[0]) * ez - (az - origin[1]) * ex) / denominator
        u = ((ax - origin[0]) * dz - (az - origin[1]) * dx) / denominator

        if 0 <= u <= 1 and (best is None or abs(t) < abs(best[0])):
            best = (t, lengths[index] + u * (lengths[index + 1] - lengths[index]))

    return best


def _sampled(points) -> list[Point]:
    result = [points[0]]

    for a, b in pairwise(points):
        count = max(1, math.ceil(math.dist(a, b) / SAMPLE))
        result += [
            (a[0] + (b[0] - a[0]) * step / count, a[1] + (b[1] - a[1]) * step / count)
            for step in range(1, count + 1)
        ]

    return result


def _lengths(lane: RoadLane) -> list[float]:
    lengths = [0.0]

    for a, b in pairwise(lane.points):
        lengths.append(lengths[-1] + math.dist(a, b))

    return lengths
