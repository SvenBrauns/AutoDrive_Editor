import math

import pytest
from costmap_helpers import make_costmap
from test_junction import VEHICLE, connect, reachable, road, two_lane_road

from autodrive_editor.editing.junction import CurveKind, road_lanes, roads_across, stem_poses
from autodrive_editor.editing.junction_box import BOX_MARGIN, box_command, plan_box
from autodrive_editor.editing.route_finder import Vehicle
from autodrive_editor.model.autodrive_data import AutoDriveData
from autodrive_editor.model.connections import ConnectionType, get_connection_type

# Stem heading south from the east-bound lane (z = 0) of two_lane_road; the west-bound lane at
# z = -4 is the far one. Stem lanes 5.5 m apart: the in-lane at x = -2.75, the out-lane at 2.75.
FOOT = (0.0, 0.0)
SOUTH = math.pi / 2
GAP = 5.5


def offset_road():
    """Like two_lane_road, nodes 5 m off the tens (east-bound 1–13 at x = -65..55), so no box
    point lies within 1 m of a node."""

    data = AutoDriveData()
    road(data, 1, [(x, 0.0) for x in range(-65, 61, 10)])
    road(data, 101, [(x, -4.0) for x in range(65, -61, -10)])

    return data


def box_crossing_road():
    """two_lane_road with a side road to the north in right-hand traffic: its north-bound lane
    at x = 3 starts at node 201 (z = -30), where turn curves from both road lanes meet; its
    south-bound lane at x = -3 ends at node 211, where turn curves to both road lanes split."""

    data = two_lane_road()
    road(data, 201, [(3.0, -30.0), (3.0, -40.0), (3.0, -50.0)])
    road(data, 211, [(-3.0, -50.0), (-3.0, -40.0), (-3.0, -30.0)])

    for first_id, branch, source_id, target_id in (
        (301, [(-20.0, -8.0), (0.0, -20.0)], 4, 201),
        (311, [(20.0, -12.0), (5.0, -22.0)], 104, 201),
        (321, [(0.0, -20.0), (20.0, -8.0)], 213, 10),
        (331, [(-5.0, -20.0), (-25.0, -6.0)], 213, 110),
    ):
        road(data, first_id, branch)
        connect(data, source_id, first_id)
        connect(data, first_id + 1, target_id)

    return data


def close(points):
    return [pytest.approx(point) for point in points]


def no_height(data, x, z):
    return 0.0


def connection_type(data, source_id, target_id):
    source, target = data.nodes[source_id], data.nodes[target_id]

    if target_id not in source.outgoing:
        return None

    return get_connection_type(source, target)


def build(data, plan, tip=(0.0, 20.0)):
    stem = stem_poses(plan.junction, tip, 5.0)
    command = box_command(data, plan, 5.0, no_height, stem=stem, gap=GAP)
    command.apply()

    def node_at(point):
        return next(
            node.node_id
            for node in data.nodes.values()
            if math.dist((node.x, node.z), point) < 1e-6
        )

    return command, node_at


def test_a_box_needs_two_one_way_lanes_and_a_two_lane_stem():
    data = AutoDriveData()
    road(data, 1, [(x, 0.0) for x in range(-60, 61, 10)], ConnectionType.DUAL)

    assert plan_box(road_lanes(data, 7, 8), FOOT, SOUTH, GAP) is None
    assert plan_box(road_lanes(two_lane_road(), 7, 8), FOOT, SOUTH, 0.0) is None


def test_the_box_reaches_7_m_beyond_the_outer_lanes():
    plan = plan_box(road_lanes(offset_road(), 7, 8), FOOT, SOUTH, GAP)

    # The stem starts at the near edge, 7 m south of the near lane.
    assert plan.junction == pytest.approx((0.0, BOX_MARGIN, SOUTH))
    assert plan.centre == pytest.approx((0.0, -2.0))
    assert sorted(plan.crossings) == close([(-2.75, -4), (-2.75, 0), (2.75, -4), (2.75, 0)])
    near, far = plan.road
    assert [end.point for end in near.ends] == close([(-9.75, 0), (-2.75, 0), (2.75, 0), (9.75, 0)])
    assert [end.point for end in far.ends] == close(
        [(9.75, -4), (2.75, -4), (-2.75, -4), (-9.75, -4)]
    )
    # A half box: the stem lanes start and end at the far lane.
    assert plan.stem == [
        close([(-2.75, -4), (-2.75, 0), (-2.75, 7)]),
        close([(2.75, 7), (2.75, 0), (2.75, -4)]),
    ]
    assert plan.missing == [] and plan.blocked == []


def test_right_turns_are_arcs_from_box_edge_to_box_edge():
    plan = plan_box(road_lanes(offset_road(), 7, 8), FOOT, SOUTH, GAP)

    turn_in, turn_out = plan.curves
    assert turn_in.kind == CurveKind.IN and turn_out.kind == CurveKind.OUT
    assert turn_in.points[0] == pytest.approx((-9.75, 0)) and turn_in.radius == BOX_MARGIN
    assert turn_in.points[-1] == pytest.approx((-2.75, 7))
    assert turn_out.points[0] == pytest.approx((2.75, 7))
    assert turn_out.points[-1] == pytest.approx((9.75, 0))

    for point in turn_in.points:
        assert math.dist(point, (-9.75, 7)) == pytest.approx(BOX_MARGIN, abs=0.01)


def test_box_command_shares_crossing_nodes_and_makes_the_arms_two_way():
    data = two_lane_road()
    plan = plan_box(road_lanes(data, 7, 8), FOOT, SOUTH, GAP)

    command, node_at = build(data, plan)

    assert data.validate_connections() == []
    centre = node_at((0, -2))
    near_in, near_out = node_at((-2.75, 0)), node_at((2.75, 0))
    far_in, far_out = node_at((-2.75, -4)), node_at((2.75, -4))
    # Box edges on the road lie within 1 m of nodes 6, 8 (east-bound) and 106, 108 (west-bound).
    assert connection_type(data, 6, near_in) == ConnectionType.DUAL
    assert connection_type(data, near_in, 7) == ConnectionType.REGULAR
    assert connection_type(data, 7, near_out) == ConnectionType.REGULAR
    assert connection_type(data, 7, 6) is None and connection_type(data, 8, 7) is None
    assert connection_type(data, near_out, 8) == ConnectionType.DUAL
    assert connection_type(data, 5, 6) == ConnectionType.REGULAR
    assert connection_type(data, 106, far_out) == ConnectionType.DUAL
    assert connection_type(data, far_out, 107) == ConnectionType.REGULAR
    # Stem lanes: one-way between the crossings, two-way out to the near edge.
    assert connection_type(data, far_in, near_in) == ConnectionType.REGULAR
    assert connection_type(data, near_in, node_at((-2.75, 7))) == ConnectionType.DUAL
    assert connection_type(data, near_out, far_out) == ConnectionType.REGULAR
    assert connection_type(data, node_at((2.75, 7)), near_out) == ConnectionType.DUAL
    for crossing in (near_in, near_out, far_in, far_out):
        assert connection_type(data, centre, crossing) == ConnectionType.DUAL


def test_every_movement_of_a_half_box_is_possible():
    data = two_lane_road()
    plan = plan_box(road_lanes(data, 7, 8), FOOT, SOUTH, GAP)

    _, node_at = build(data, plan)

    in_end, out_end = node_at((-2.75, 20)), node_at((2.75, 20))
    assert data.nodes[in_end].outgoing == set()
    assert {in_end, 13, 113} <= reachable(data, 1)
    assert {in_end, 13, 113} <= reachable(data, 101)
    assert {13, 113} <= reachable(data, out_end)


def test_right_turns_leave_and_join_the_lanes_at_the_box_edge():
    data = two_lane_road()
    plan = plan_box(road_lanes(data, 7, 8), FOOT, SOUTH, GAP)

    _, node_at = build(data, plan)

    # Node 6 is the box edge of the east-bound lane: on along the lane, and the right turn.
    assert len(data.nodes[6].outgoing) == 2
    assert len(data.nodes[8].incoming) == 2
    assert len(data.nodes[node_at((-2.75, 7))].incoming) == 2


def test_a_road_across_gets_the_fourth_arm_and_its_right_turns():
    data = box_crossing_road()
    lanes = road_lanes(data, 7, 8)
    across = roads_across(data, lanes, FOOT, SOUTH)

    plan = plan_box(lanes, FOOT, SOUTH, GAP, across=across)

    assert plan.missing == []
    far_edge = -4 - BOX_MARGIN
    assert plan.stem[0][0] == pytest.approx((-2.75, far_edge))
    assert plan.stem[1][-1] == pytest.approx((2.75, far_edge))
    straight = [curve for curve in plan.curves if curve.across]
    assert [(curve.kind, curve.road_end.node_id) for curve in straight] == [
        (CurveKind.OUT, 201),
        (CurveKind.IN, 213),
    ]
    assert len(plan.curves) == 6

    _, node_at = build(data, plan)

    assert data.validate_connections() == []
    in_end, out_end = node_at((-2.75, 20)), node_at((2.75, 20))
    assert in_end in reachable(data, 211)
    assert 202 in reachable(data, out_end)
    assert 202 in reachable(data, 101)
    assert 13 in reachable(data, 211)
    far_in = node_at((-2.75, -4))
    assert connection_type(data, node_at((-2.75, far_edge)), far_in) == ConnectionType.DUAL


def test_a_far_arm_that_does_not_fit_is_listed_and_left_out():
    data = box_crossing_road()
    lanes = road_lanes(data, 7, 8)
    across = roads_across(data, lanes, FOOT, SOUTH)
    costmap = make_costmap(blocked=[(-10, -28, 10, -20)])

    plan = plan_box(lanes, FOOT, SOUTH, GAP, costmap, VEHICLE, across=across)

    assert plan.missing == ["No straight on to the north", "No straight on from the north"]
    assert plan.stem[0][0] == pytest.approx((-2.75, -4))
    assert len(plan.curves) == 2


def test_box_pieces_on_blocked_ground_are_built_and_listed():
    # One cell on the arc of the right turn in, clear of the lanes for a narrow vehicle.
    costmap = make_costmap(blocked=[(-6, 1, -5, 2)])
    narrow = Vehicle(turning_radius=10, width=1, margin=0)

    plan = plan_box(road_lanes(two_lane_road(), 7, 8), FOOT, SOUTH, GAP, costmap, narrow)

    assert plan.blocked == ["right turn from the west to the south"]
    assert len(plan.curves) == 2


def test_no_box_where_the_road_part_is_too_short():
    data = AutoDriveData()
    road(data, 1, [(x, 0.0) for x in range(-8, 9, 8)])
    road(data, 101, [(x, -4.0) for x in range(8, -9, -8)])

    assert plan_box(road_lanes(data, 2, 3), FOOT, SOUTH, GAP) is None


def test_a_crossing_on_a_lane_node_is_that_node():
    data = two_lane_road()
    # The in-lane crosses the east-bound lane at node 7 (x = 0).
    plan = plan_box(road_lanes(data, 7, 8), (2.75, 0.0), SOUTH, GAP)

    near, _ = plan.road
    assert [end.node_id for end in near.ends][1:3] == [7, None]

    build(data, plan, tip=(2.75, 20.0))

    assert data.validate_connections() == []
