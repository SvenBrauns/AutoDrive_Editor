import math
from collections import defaultdict

import pytest

from autodrive_editor.editing.station_layout import StationSettings, StopChoice, lane_points
from autodrive_editor.editing.station_yard import (
    StopShape,
    YardStop,
    default_shapes,
    joined_ends,
    plan_yard,
    yard_command,
)
from autodrive_editor.editing.yard_road import yard_road
from autodrive_editor.file_io.savegame_stations import Stop, StopKind
from autodrive_editor.model.autodrive_data import (
    REGULAR_FLAG,
    SUBPRIO_FLAG,
    AutoDriveData,
    NodeData,
)
from autodrive_editor.model.connections import ConnectionType

SETTINGS = StationSettings()
# A Through road along the x axis, driven towards +x.
ROAD = yard_road([(0, 0), (200, 0)], radius=6.0)


def stop(x, z, heading=90.0, kind=StopKind.SELL, name="A"):
    return Stop("b.xml", "1", name, kind, (), (x, 0, z), heading, True)


def yard(*stops, shape=StopShape.BRANCH, road=ROAD):
    choices = [YardStop(StopChoice(s, s.name, "G", s.heading), shape) for s in stops]

    plan = plan_yard(road, choices, SETTINGS, radius=6.0)
    points = plan.piece.points
    # No connection jumps: all but a bay's reverse one (along its stub) are at most the spacing.
    connections = [(s, t) for s, t, k in plan.piece.connections if k != ConnectionType.REVERSE]
    assert all(math.dist(points[s], points[t]) <= 12.01 for s, t in connections)

    return plan


def reachable(piece, start):
    """Indices reachable from start, driving forward, both ways on dual and back on reverse."""

    following = defaultdict(set)

    for source, target, kind in piece.connections:
        following[source].add(target)

        if kind == ConnectionType.DUAL:
            following[target].add(source)

    seen, todo = {start}, [start]

    while todo:
        for nxt in following[todo.pop()] - seen:
            seen.add(nxt)
            todo.append(nxt)

    return seen


def marker_point(plan):
    (index, _, _), *_ = plan.piece.markers
    return plan.piece.points[index]


def test_default_shapes_by_distance_kind_and_gap():
    stops = [
        stop(50, 15),
        stop(60, 15),
        stop(100, 40),
        stop(150, 20, kind=StopKind.ANIMALS),
    ]

    assert default_shapes(stops, ROAD) == [
        StopShape.BRANCH,
        StopShape.CHAIN,
        StopShape.LANE,
        StopShape.BAY,
    ]


def test_branch_leaves_and_rejoins_the_road_and_runs_in_its_direction():
    # The arrow points against the road (-x): the lane is turned round.
    plan = yard(stop(100, 15, heading=270.0))
    start, end = plan.ends

    assert plan.problems == []
    assert marker_point(plan) == pytest.approx((108, 15))
    marker = plan.piece.markers[0][0]
    assert marker in reachable(plan.piece, start) and end in reachable(plan.piece, marker)
    assert plan.piece.flags[marker] == SUBPRIO_FLAG and plan.piece.flags[start] == REGULAR_FLAG


def test_stops_in_a_chain_share_one_branch():
    plan = yard(stop(100, 15), stop(112, 15), shape=StopShape.CHAIN)
    forks = [i for i in range(len(plan.piece.points)) if _out(plan.piece, i) > 1]

    assert plan.problems == [] and len(plan.piece.markers) == 2
    assert len(forks) == 1


def test_back_in_bay_has_dual_line_from_the_marker_and_one_reverse_connection():
    # The axis runs across the road; the marker lies the offset from the stop towards it.
    plan = yard(stop(100, 30, heading=0.0), shape=StopShape.BAY)
    start, end = plan.ends
    marker = plan.piece.markers[0][0]
    kinds = [kind for *_, kind in plan.piece.connections]

    assert plan.problems == []
    assert plan.piece.points[marker] == pytest.approx((100, 22))
    assert kinds.count(ConnectionType.REVERSE) == 1
    assert marker in reachable(plan.piece, start) and end in reachable(plan.piece, marker)


def test_bay_without_room_to_the_road_is_listed():
    plan = yard(stop(100, 8, heading=0.0), shape=StopShape.BAY)

    assert len(plan.problems) == 1 and plan.piece.markers == []


def test_loop_ring_closes_on_its_first_node_and_takes_the_stops():
    corners = [(0, 0), (20, 0), (120, 0), (120, 60), (20, 60), (20, 0)]
    road = yard_road(corners, radius=6.0, closes_at=1)
    plan = yard(stop(70, 15), road=road)
    start, end = plan.ends

    assert end is None and plan.problems == []
    marker = plan.piece.markers[0][0]
    assert start in reachable(plan.piece, marker)
    assert math.dist(plan.piece.points[start], (0, 0)) < 1e-6


def network():
    data = AutoDriveData()

    for node in [
        NodeData(1, -1, 0, 1, outgoing={2}),
        NodeData(2, 0, 0, 0, incoming={1}, outgoing={3}),
        NodeData(3, 1, 0, 1, incoming={2}),
        NodeData(4, 201, 0, 1, outgoing={5}),
        NodeData(5, 200, 0, 0, incoming={4}),
    ]:
        data.add_node(node)

    return data


def test_road_ends_join_only_nodes_whose_direction_fits():
    data = network()
    corners = [(0.5, 0.5), (100, 0), (199, 1)]

    # Node 2 is driven to; node 5 is not driven from, so the end stays open.
    moved, joined = joined_ends(data, corners, [2, None, 5], loop=False)
    assert joined == (2, None) and moved == [(0, 0), (100, 0), (199, 1)]

    # Node 1 is not driven to; node 4 is driven from.
    assert joined_ends(data, corners, [1, None, 4], loop=False)[1] == (None, 4)
    # A Loop's two-way stem needs a node driven to and from; a Loop has no end.
    assert joined_ends(data, corners, [3, None, 4], loop=True)[1] == (None, None)
    assert joined_ends(data, corners, [2, None, 4], loop=True)[1] == (2, None)


def test_yard_command_adds_road_stops_and_lanes_in_one_step_on_the_joined_nodes():
    data = network()
    corners, joined = joined_ends(data, [(0, 0), (200, 0)], [2, 5], loop=False)
    road = yard_road(corners, radius=6.0)
    choices = [YardStop(StopChoice(stop(100, 15), "A", "G", 90.0), StopShape.BRANCH)]
    plan = plan_yard(road, choices, SETTINGS, radius=6.0)
    lane = StopChoice(stop(100, 80, name="B"), "B", "G", 90.0)
    before = len(data.nodes)

    command = yard_command(data, plan, (2, None), [lane], SETTINGS, lambda _, x, z: 7.0)
    command.redo()

    lane_count = len(lane_points(lane.stop, SETTINGS, 90.0)[0])
    added = len(plan.piece.points) - 1 + lane_count
    assert len(data.nodes) == before + added
    assert {marker.name for marker in data.markers.values()} == {"A", "B"}
    assert data.nodes[2].outgoing - {3}
    assert all(node.y == 7.0 for node in data.nodes.values() if node.node_id > 5 and node.z < 50)

    command.undo()
    assert len(data.nodes) == before and not data.markers


def _out(piece, index):
    return sum(1 for source, _, _ in piece.connections if source == index)


def test_branch_leaves_the_road_on_a_straight_not_on_the_corner_arc():
    # The arc runs from (94, 0) to (100, 6); 15 m before the lane would be on it.
    road = yard_road([(0, 0), (100, 0), (100, 100)], radius=6.0)

    for z in (25, 30):
        plan = yard(stop(110, z, heading=180.0), road=road)
        points, connections = plan.piece.points, plan.piece.connections
        fork = next(s for s in range(len(points)) if sum(c[0] == s for c in connections) == 2)
        x, fork_z = points[fork]

        assert plan.problems == []
        assert (fork_z == pytest.approx(0) and x <= 93) or (x == pytest.approx(100) and fork_z >= 7)


def test_road_part_just_over_the_spacing_gets_no_longer_connection():
    # The yard helper checks every connection is at most the spacing; this branch's rejoin
    # point once left a 12.2 m road piece with no node in it.
    yard(stop(85, 10), road=yard_road([(0, 0), (100, 0), (100, 100)], radius=6.0))
