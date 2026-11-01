import math
from itertools import pairwise

import pytest
from costmap_helpers import make_costmap

from autodrive_editor.editing.junction import (
    BOTH,
    MIN_RADIUS,
    NODE_TURN,
    CurveKind,
    Stem,
    foot_on_lane,
    is_on_two_way_road,
    junction_command,
    junction_distance,
    lane_poses,
    plan_junction,
    road_lanes,
    roads_across,
    stem_poses,
    uses_two_lanes,
)
from autodrive_editor.editing.route_finder import Route, Vehicle
from autodrive_editor.model.autodrive_data import AutoDriveData, MarkerData, NodeData
from autodrive_editor.model.connections import (
    CONNECTION_STATES,
    ConnectionType,
    get_connection_type,
    write_connection_state,
)

VEHICLE = Vehicle(turning_radius=10, width=3, margin=0.5)
# Junction 15 m south of the road, the stem heading south (z grows southwards).
JUNCTION = (0.0, 15.0, math.pi / 2)
# Where the curves meet: one yard radius (6 m) south of the east-bound lane.
MEETING = (0.0, 6.0, math.pi / 2)


def road(data, first_id, points, connection_type=ConnectionType.REGULAR):
    """Nodes at the points, connected in order. Returns their IDs."""

    ids = list(range(first_id, first_id + len(points)))

    for node_id, (x, z) in zip(ids, points, strict=True):
        data.add_node(NodeData(node_id, x, 0, z))

    for source, target in pairwise(ids):
        write_connection_state(data, source, target, CONNECTION_STATES[connection_type])

    return ids


def two_lane_road():
    """East-bound lane at z = 0 (IDs 1–13), west-bound lane at z = -4 (IDs 101–113)."""

    data = AutoDriveData()
    road(data, 1, [(x, 0.0) for x in range(-60, 61, 10)])
    road(data, 101, [(x, -4.0) for x in range(60, -61, -10)])

    return data


def headings(points):
    return [math.atan2(b[1] - a[1], b[0] - a[0]) for a, b in pairwise(points) if a != b]


def max_turn(points):
    """Largest heading change per metre along the points."""

    pieces = [(a, b) for a, b in pairwise(points) if math.dist(a, b) > 1e-6]
    values = []

    for (a, b), (c, d) in pairwise(pieces):
        turn = abs(math.remainder(headings([c, d])[0] - headings([a, b])[0], math.tau))
        values.append(turn / ((math.dist(a, b) + math.dist(c, d)) / 2))

    return max(values)


def test_road_lanes_of_a_two_lane_road():
    lanes = road_lanes(two_lane_road(), 7, 8)

    assert len(lanes) == 2
    assert lanes[0].node_ids == tuple(range(1, 14))
    assert lanes[1].node_ids == tuple(range(101, 114))


def test_road_lanes_of_a_two_way_road():
    data = AutoDriveData()
    road(data, 1, [(x, 0.0) for x in range(-60, 61, 10)], ConnectionType.DUAL)

    lanes = road_lanes(data, 7, 8)

    assert len(lanes) == 2
    assert lanes[1].node_ids == lanes[0].node_ids[::-1]


def test_road_lanes_follow_the_road_only_so_far():
    data = AutoDriveData()
    road(data, 1, [(x, 0.0) for x in range(-500, 501, 10)])

    lane = road_lanes(data, 50, 51)[0]

    assert 60 < lane.points[-1][0] < 120
    assert -120 < lane.points[0][0] < -60


def test_four_curves_meet_at_the_junction_and_leave_the_lanes_tangentially():
    data = two_lane_road()
    plan = plan_junction(road_lanes(data, 7, 8), JUNCTION, BOTH, 6.0, None, VEHICLE)

    assert plan.missing == []
    assert len(plan.curves) == 4

    for curve in plan.curves:
        lane_z = curve.road_end.point[1]
        assert lane_z in (0.0, -4.0)
        assert curve.radius == 6.0
        assert max_turn(curve.points) <= 1 / 6 + 0.02

        if curve.kind == CurveKind.IN:
            assert curve.points[-1] == pytest.approx(JUNCTION[:2])
            road_heading = headings(curve.points[:2])[0]
            end_heading = headings(curve.points[-2:])[0]
        else:
            assert curve.points[0] == pytest.approx(JUNCTION[:2])
            road_heading = headings(curve.points[-2:])[0]
            end_heading = headings(curve.points[:2])[0] + math.pi

        lane_heading = 0.0 if lane_z == 0.0 else math.pi
        assert math.cos(road_heading - lane_heading) > 0.99
        assert math.cos(end_heading - JUNCTION[2]) > 0.99


def test_curves_on_a_curved_road_leave_it_tangentially():
    # East-bound lane on a circle of 60 m radius around (0, 60), bending away from the junction
    # side: the road runs north of the circle's centre.
    data = AutoDriveData()
    points = [
        (60 * math.sin(angle), 60 - 60 * math.cos(angle))
        for angle in (math.radians(degrees) for degrees in range(-60, 61, 5))
    ]
    road(data, 1, points)
    junction = (0.0, -15.0, -math.pi / 2)

    plan = plan_junction(road_lanes(data, 12, 13), junction, BOTH, 6.0, None, VEHICLE)

    assert len(plan.curves) == 2

    for curve in plan.curves:
        x, z = curve.road_end.point
        # Tangent of the circle at the road end, in driving direction.
        tangent = math.atan2(x, 60 - z)
        if curve.kind == CurveKind.IN:
            heading = headings(curve.points[:2])[0]
        else:
            heading = headings(curve.points[-2:])[0]
        assert math.cos(heading - tangent) > 0.98


def test_a_blocked_curve_moves_along_the_road_or_tightens():
    data = two_lane_road()
    lanes = road_lanes(data, 7, 8)[:1]
    free = plan_junction(lanes, JUNCTION, (CurveKind.IN,), 6.0, make_costmap(), VEHICLE)
    # A block where the shortest curve in runs.
    x, z = free.curves[0].points[len(free.curves[0].points) // 3]
    blocked = make_costmap(
        blocked=[(math.floor(x) - 1, math.floor(z) - 1, math.floor(x) + 2, math.floor(z) + 2)]
    )

    plan = plan_junction(lanes, JUNCTION, (CurveKind.IN,), 6.0, blocked, VEHICLE)

    assert plan.missing == []
    assert plan.curves[0].points != free.curves[0].points
    assert plan.curves[0].radius >= MIN_RADIUS


def test_a_curve_that_does_not_fit_is_listed():
    lanes = road_lanes(two_lane_road(), 7, 8)[:1]
    # A wall between the road and the junction, all along the road.
    wall = make_costmap(blocked=[(-90, 5, 90, 8)])

    plan = plan_junction(lanes, JUNCTION, (CurveKind.IN,), 6.0, wall, VEHICLE)

    assert plan.curves == []
    # East-bound lane, junction to the south: a right turn for vehicles from the west.
    assert plan.missing == ["No right turn in from the west"]
    # Shown as a gap from the junction to the lane.
    assert plan.gaps == [(JUNCTION[:2], pytest.approx((JUNCTION[0], 0)))]


def test_the_route_finder_builds_a_curve_that_does_not_fit():
    lanes = road_lanes(two_lane_road(), 7, 8)[:1]
    wall = make_costmap(blocked=[(-90, 5, 90, 8)])
    requests = []

    def find_route(request):
        requests.append(request)
        return Route([request.start, (0.0, 7.0), request.goal], [0, 2], [False] * 3)

    plan = plan_junction(
        lanes, JUNCTION, (CurveKind.IN,), 6.0, wall, VEHICLE, find_route=find_route
    )

    assert plan.missing == []
    assert plan.curves[0].searched
    assert requests[0].goal == JUNCTION[:2]
    assert requests[0].goal_headings == (JUNCTION[2],)
    assert requests[0].turning_radius == 6.0


def test_an_existing_lane_node_is_used_when_close():
    # Lane nodes every metre: every place along the lane is a node.
    data = AutoDriveData()
    road(data, 1, [(float(x), 0.0) for x in range(-60, 61)])

    plan = plan_junction(road_lanes(data, 60, 61)[:1], JUNCTION, BOTH, 6.0, None, VEHICLE)

    assert all(curve.road_end.node_id is not None for curve in plan.curves)


def test_junction_command_splits_the_lanes_and_connects_the_curves():
    data = two_lane_road()
    plan = plan_junction(road_lanes(data, 7, 8), MEETING, BOTH, 6.0, None, VEHICLE)
    command = junction_command(data, plan, MEETING, 5.0, lambda data, x, z: 0.0)

    command.apply()

    assert data.validate_connections() == []
    # From the near lane directly, from the far lane over the stem.
    junction = next(node for node in command.new_nodes if (node.x, node.z) == MEETING[:2])
    assert len(junction.incoming) == 2
    assert len(junction.outgoing) == 2

    # Each lane is still one chain from end to end, now through the split nodes.
    for first, last in ((1, 13), (101, 113)):
        node_id, steps = first, 0
        while node_id != last:
            on_lane = [
                i for i in data.nodes[node_id].outgoing if data.nodes[i].z == data.nodes[first].z
            ]
            assert len(on_lane) == 1
            assert (
                get_connection_type(data.nodes[node_id], data.nodes[on_lane[0]])
                == ConnectionType.REGULAR
            )
            node_id, steps = on_lane[0], steps + 1
        assert steps > 12


def test_curve_ends_at_the_same_place_share_a_node():
    data = AutoDriveData()
    road(data, 1, [(x, 0.0) for x in range(-60, 61, 10)], ConnectionType.DUAL)
    plan = plan_junction(road_lanes(data, 7, 8), JUNCTION, BOTH, 6.0, None, VEHICLE)
    ends = [curve.road_end.point for curve in plan.curves]
    command = junction_command(data, plan, JUNCTION, 5.0, lambda data, x, z: 0.0)

    command.apply()

    # In from the west and out to the west leave and join the road at the same place.
    distinct = {(round(x), round(z)) for x, z in ends}
    on_road = [node for node in command.new_nodes if node.z == 0.0]
    assert len(on_road) == len(distinct) < 4
    assert data.validate_connections() == []


def test_given_junction_node_is_used():
    data = two_lane_road()
    data.add_node(NodeData(500, MEETING[0], 0, MEETING[1]))
    plan = plan_junction(road_lanes(data, 7, 8), MEETING, (CurveKind.IN,), 6.0, None, VEHICLE)

    command = junction_command(data, plan, MEETING, 5.0, lambda data, x, z: 0.0, 500)
    command.apply()

    assert len(data.nodes[500].incoming) == 2


def test_marker_ids_are_not_lane_snap_targets():
    data = AutoDriveData()
    road(data, 1, [(float(x), 0.0) for x in range(-60, 61)])
    data.add_marker(MarkerData(55, "Silo", "All"))

    plan = plan_junction(
        road_lanes(data, 60, 61)[:1], JUNCTION, BOTH, 6.0, None, VEHICLE, frozenset({55})
    )

    assert all(curve.road_end.node_id != 55 for curve in plan.curves)


def test_curve_nodes_are_close_enough_for_the_turn():
    data = two_lane_road()
    plan = plan_junction(road_lanes(data, 7, 8)[:1], MEETING, (CurveKind.IN,), 6.0, None, VEHICLE)
    command = junction_command(data, plan, MEETING, 5.0, lambda data, x, z: 0.0)

    command.apply()

    # 22.5° of a 6 m radius: 2.4 m, evened out over the curve.
    for node in command.new_nodes:
        for target_id in node.outgoing & command.new_ids:
            target = data.nodes[target_id]
            assert math.dist((node.x, node.z), (target.x, target.z)) < 3.0


def test_one_lane_only_gives_two_curves():
    data = AutoDriveData()
    road(data, 1, [(x, 0.0) for x in range(-60, 61, 10)])

    plan = plan_junction(road_lanes(data, 7, 8), JUNCTION, BOTH, 6.0, None, VEHICLE)

    assert len(plan.curves) == 2


def test_curves_share_the_stem_line_before_a_far_junction():
    data = two_lane_road()
    plan = plan_junction(road_lanes(data, 7, 8), JUNCTION, BOTH, 6.0, None, VEHICLE)
    command = junction_command(data, plan, JUNCTION, 5.0, lambda data, x, z: 0.0)

    command.apply()

    # The near lane's curves reach the stem 6 m from the road, the far lane's 2 m from it; from
    # there to the junction the stem is one two-way line.
    stem = sorted(
        (node for node in command.new_nodes if abs(node.x) < 1e-6 and node.z > 1),
        key=lambda node: node.z,
    )
    assert [round(node.z) for node in (stem[0], stem[-1])] == [2, 15]
    assert any(round(node.z) == 6 for node in stem)
    for a, b in pairwise(stem):
        assert get_connection_type(a, b) == ConnectionType.DUAL
    assert data.validate_connections() == []


def test_junction_distance_is_a_radius_beyond_the_farthest_lane():
    lanes = road_lanes(two_lane_road(), 7, 8)

    assert junction_distance(lanes, (0.0, 0.0), math.pi / 2, 6.0) == pytest.approx(6.0)
    assert junction_distance(lanes, (0.0, 0.0), -math.pi / 2, 6.0) == pytest.approx(10.0)


def test_a_two_way_stem_continues_from_the_junction():
    data = two_lane_road()
    plan = plan_junction(road_lanes(data, 7, 8), MEETING, BOTH, 6.0, None, VEHICLE)
    command = junction_command(
        data, plan, MEETING, 5.0, lambda data, x, z: 0.0, stem=stem_poses(MEETING, (0, 18), 5.0)
    )

    command.apply()

    stem = sorted(
        (n for n in command.new_nodes if n.x == pytest.approx(0) and n.z >= 6), key=lambda n: n.z
    )
    assert [round(n.z) for n in stem] == [6, 10, 14, 18]
    for a, b in pairwise(stem):
        assert get_connection_type(a, b) == ConnectionType.DUAL


def test_junction_distance_leaves_room_for_the_sharper_turn_of_an_oblique_stem():
    lanes = road_lanes(two_lane_road(), 7, 8)
    heading = math.radians(60)

    # The west-bound lane at z = -4 is not crossed going south-east from the foot.
    expected = 6.0 * (1 + math.cos(heading)) / math.sin(heading)

    assert junction_distance(lanes, (0.0, 0.0), heading, 6.0) == pytest.approx(expected)


def test_curves_of_an_oblique_junction_are_arcs_without_detours():
    data = two_lane_road()
    lanes = road_lanes(data, 7, 8)
    heading = math.radians(60)
    distance = junction_distance(lanes, (0.0, 0.0), heading, 6.0)
    junction = (distance * math.cos(heading), distance * math.sin(heading), heading)

    plan = plan_junction(lanes[:1], junction, BOTH, 6.0, None, VEHICLE)

    # Each curve is no longer than its arc plus the straight part along the stem.
    for curve in plan.curves:
        length = sum(math.dist(a, b) for a, b in pairwise(curve.points))
        assert length < 6.0 * math.radians(120) + distance + 1


def test_auto_stem_has_two_lanes_on_a_road_of_two_one_way_lanes():
    two_lanes = road_lanes(two_lane_road(), 7, 8)
    dual = AutoDriveData()
    road(dual, 1, [(x, 0.0) for x in range(-60, 61, 10)], ConnectionType.DUAL)
    dual_lanes = road_lanes(dual, 7, 8)

    assert uses_two_lanes(Stem.AUTO, two_lanes)
    assert not uses_two_lanes(Stem.AUTO, dual_lanes)
    assert not uses_two_lanes(Stem.AUTO, two_lanes[:1])
    assert not uses_two_lanes(Stem.TWO_WAY, two_lanes)
    assert uses_two_lanes(Stem.TWO_LANES, dual_lanes)


def test_lane_poses_put_the_in_lane_on_the_right_of_the_way_into_the_yard():
    # Driving south into the yard, the right is west (smaller x).
    in_pose, out_pose = lane_poses(JUNCTION, 5.5)

    assert in_pose == pytest.approx((-2.75, 15.0, math.pi / 2))
    assert out_pose == pytest.approx((2.75, 15.0, math.pi / 2))


def test_junction_distance_with_a_lane_gap_leaves_room_for_both_lanes():
    lanes = road_lanes(two_lane_road(), 7, 8)
    heading = math.radians(60)

    # The out-lane starts 2.75 m to the left, where the line along the heading crosses the
    # east-bound lane further on.
    later = 2.75 * math.cos(heading) / math.sin(heading)
    expected = later + 6.0 * (1 + math.cos(heading)) / math.sin(heading)

    assert junction_distance(lanes, (0.0, 0.0), heading, 6.0, gap=5.5) == pytest.approx(expected)


def test_with_a_lane_gap_curves_in_and_out_meet_at_their_own_lane():
    plan = plan_junction(
        road_lanes(two_lane_road(), 7, 8), JUNCTION, BOTH, 6.0, None, VEHICLE, gap=5.5
    )
    in_pose, out_pose = lane_poses(JUNCTION, 5.5)

    assert plan.missing == []
    assert len(plan.curves) == 4

    for curve in plan.curves:
        if curve.kind == CurveKind.IN:
            assert curve.points[-1] == pytest.approx(in_pose[:2])
        else:
            assert curve.points[0] == pytest.approx(out_pose[:2])


def reachable(data, start_id):
    seen, todo = {start_id}, [start_id]

    while todo:
        for target_id in data.nodes[todo.pop()].outgoing - seen:
            seen.add(target_id)
            todo.append(target_id)

    return seen


def test_a_two_lane_stem_is_two_one_way_lanes_into_and_out_of_the_yard():
    data = two_lane_road()
    plan = plan_junction(road_lanes(data, 7, 8), JUNCTION, BOTH, 6.0, None, VEHICLE, gap=5.5)
    command = junction_command(
        data,
        plan,
        JUNCTION,
        5.0,
        lambda data, x, z: 0.0,
        stem=stem_poses(JUNCTION, (0, 27), 5.0),
        gap=5.5,
    )

    command.apply()

    assert data.validate_connections() == []
    new_ids = command.new_ids
    for node_id in new_ids:
        for target_id in data.nodes[node_id].outgoing & new_ids:
            pair = (data.nodes[node_id], data.nodes[target_id])
            assert get_connection_type(*pair) == ConnectionType.REGULAR

    def stem_end(x):
        return next(
            node.node_id
            for node in command.new_nodes
            if node.x == pytest.approx(x) and node.z == pytest.approx(27.0)
        )

    in_end, out_end = stem_end(-2.75), stem_end(2.75)
    # From both lanes into the yard, from the yard to both lanes; the in-lane ends in the yard.
    assert in_end in reachable(data, 1) & reachable(data, 101)
    assert {13, 113} <= reachable(data, out_end)
    assert data.nodes[in_end].outgoing == set()


def test_a_straight_stem_runs_on_along_the_junction_heading():
    poses = stem_poses(JUNCTION, (0.0, 27.0), 5.0)

    assert [coordinate for pose in poses for coordinate in pose[:2]] == pytest.approx(
        [0, 15, 0, 19, 0, 23, 0, 27]
    )
    assert all(pose[2] == pytest.approx(math.pi / 2) for pose in poses)


def test_a_bent_stem_leaves_along_the_heading_and_bends_in_one_arc_to_the_tip():
    poses = stem_poses(JUNCTION, (10.0, 30.0), 5.0)

    assert poses[0] == pytest.approx(JUNCTION)
    assert poses[-1][:2] == pytest.approx((10.0, 30.0))
    # One arc: every point equally far from a centre on the line square to the heading.
    centre_x = (10.0**2 + 15.0**2) / (2 * 10.0)
    radii = [math.dist((x, z), (centre_x, 15.0)) for x, z, _ in poses]
    assert radii == pytest.approx([centre_x] * len(poses))
    for a, b in pairwise(poses):
        assert math.dist(a[:2], b[:2]) <= 5.0 + 1e-9
        assert abs(math.remainder(b[2] - a[2], math.tau)) <= NODE_TURN + 1e-9


def test_a_stem_to_the_junction_itself_is_only_the_junction():
    assert stem_poses(JUNCTION, JUNCTION[:2], 5.0) == [JUNCTION]


def test_foot_on_lane_is_the_closest_lane_point_with_the_lane_heading():
    lane = road_lanes(two_lane_road(), 7, 8)[0]

    assert foot_on_lane(lane, (12.0, 20.0)) == pytest.approx((12.0, 0.0, 0.0))


def test_two_way_road_nodes():
    data = two_lane_road()
    road(data, 200, [(0.0, 40.0), (10.0, 40.0)], ConnectionType.DUAL)

    assert is_on_two_way_road(data, 200)
    assert not is_on_two_way_road(data, 7)


def test_a_two_lane_stem_bent_onto_a_node_joins_both_lanes_to_it():
    data = two_lane_road()
    data.add_node(NodeData(500, 10.0, 0, 30.0))
    plan = plan_junction(road_lanes(data, 7, 8), JUNCTION, BOTH, 6.0, None, VEHICLE, gap=5.5)
    stem = stem_poses(JUNCTION, (10.0, 30.0), 5.0)
    command = junction_command(
        data, plan, JUNCTION, 5.0, lambda data, x, z: 0.0, stem=stem, gap=5.5, tip_id=500
    )

    command.apply()

    assert data.validate_connections() == []
    tip = data.nodes[500]
    assert len(tip.incoming) == 1 and len(tip.outgoing) == 1
    assert 500 in reachable(data, 1) & reachable(data, 101)
    assert {13, 113} <= reachable(data, 500)


def test_a_two_way_stem_onto_a_node_ends_two_way_there():
    data = two_lane_road()
    data.add_node(NodeData(500, 0.0, 0, 27.0))
    plan = plan_junction(road_lanes(data, 7, 8), JUNCTION, BOTH, 6.0, None, VEHICLE)
    stem = stem_poses(JUNCTION, (0.0, 27.0), 5.0)
    command = junction_command(
        data, plan, JUNCTION, 5.0, lambda data, x, z: 0.0, stem=stem, tip_id=500
    )

    command.apply()

    (last_id,) = data.nodes[500].incoming
    assert get_connection_type(data.nodes[last_id], data.nodes[500]) == ConnectionType.DUAL
    assert data.nodes[last_id].z == pytest.approx(23.0)


def connect(data, source_id, target_id):
    write_connection_state(data, source_id, target_id, CONNECTION_STATES[ConnectionType.REGULAR])


def crossing_road():
    """two_lane_road with a side road to the north: its north-bound lane at x = -3 starts at
    node 201 (z = -30), where turn curves from both road lanes meet; its south-bound lane at
    x = 3 ends at node 211 (z = -30), where turn curves to both road lanes split."""

    data = two_lane_road()
    road(data, 201, [(-3.0, -30.0), (-3.0, -40.0), (-3.0, -50.0)])

    for node_id, z in ((211, -30.0), (212, -40.0), (213, -50.0)):
        data.add_node(NodeData(node_id, 3.0, 0, z))
    for source, target in ((213, 212), (212, 211)):
        connect(data, source, target)

    # From the east-bound lane (node 4, x = -30) and the west-bound one (node 104, x = 30).
    for first_id, branch, road_id in (
        (301, [(-20.0, -8.0), (-10.0, -18.0)], 4),
        (311, [(15.0, -12.0), (2.0, -22.0)], 104),
    ):
        road(data, first_id, branch)
        connect(data, road_id, first_id)
        connect(data, first_id + 1, 201)

    # To the east-bound lane (node 10, x = 30) and the west-bound one (node 110, x = -30).
    for first_id, branch, road_id in (
        (321, [(10.0, -18.0), (20.0, -8.0)], 10),
        (331, [(-10.0, -14.0), (-25.0, -6.0)], 110),
    ):
        road(data, first_id, branch)
        connect(data, 211, first_id)
        connect(data, first_id + 1, road_id)

    return data


def test_the_road_across_is_where_turn_curves_meet_and_split_on_the_far_side():
    data = crossing_road()
    lanes = road_lanes(data, 7, 8)

    across = roads_across(data, lanes, (0.0, 0.0), math.pi / 2)

    assert [(kind, lane.node_ids) for kind, lane in across] == [
        (CurveKind.OUT, (201, 202)),
        (CurveKind.IN, (212, 211)),
    ]
    # Not when the stem leaves on the side road's side.
    assert roads_across(data, lanes, (0.0, 0.0), -math.pi / 2) == []
    # Nor when the side road lies well to the side of the stem's line.
    assert roads_across(data, lanes, (20.0, 0.0), math.pi / 2) == []


def test_straight_lanes_lead_across_to_the_road_on_the_far_side():
    data = crossing_road()
    lanes = road_lanes(data, 7, 8)
    across = roads_across(data, lanes, (0.0, 0.0), math.pi / 2)

    plan = plan_junction(lanes, JUNCTION, BOTH, 6.0, None, VEHICLE, across=across)

    assert plan.missing == []
    straight = [curve for curve in plan.curves if curve.across]
    assert [(curve.kind, curve.road_end.node_id) for curve in straight] == [
        (CurveKind.OUT, 201),
        (CurveKind.IN, 211),
    ]
    out_lane, in_lane = straight
    assert out_lane.points[0] == pytest.approx(JUNCTION[:2])
    assert out_lane.points[-1] == pytest.approx((-3.0, -30.0))
    assert in_lane.points[0] == pytest.approx((3.0, -30.0))

    command = junction_command(data, plan, JUNCTION, 5.0, lambda data, x, z: 0.0)
    command.apply()

    assert data.validate_connections() == []
    (junction_id,) = (node.node_id for node in command.new_nodes if node.z == JUNCTION[1])
    assert 202 in reachable(data, junction_id)
    assert junction_id in reachable(data, 213)


def test_straight_lanes_blocked_by_an_island_are_searched_or_listed():
    data = crossing_road()
    lanes = road_lanes(data, 7, 8)
    across = roads_across(data, lanes, (0.0, 0.0), math.pi / 2)
    costmap = make_costmap(blocked=[(-10, -20, 10, -8)])

    plan = plan_junction(lanes, JUNCTION, BOTH, 6.0, costmap, VEHICLE, across=across)

    assert plan.missing == ["No straight on to the north", "No straight on from the north"]
    assert len(plan.gaps) == 2

    def find_route(request):
        return Route(list(request.waypoints), [0, 1], [False, False])

    plan = plan_junction(
        lanes, JUNCTION, BOTH, 6.0, costmap, VEHICLE, find_route=find_route, across=across
    )

    assert plan.missing == []
    assert all(curve.searched for curve in plan.curves if curve.across)
