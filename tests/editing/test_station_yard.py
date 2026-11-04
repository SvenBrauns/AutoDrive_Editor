import math
from collections import defaultdict

import pytest

from autodrive_editor.editing.station_layout import StationSettings, StopChoice
from autodrive_editor.editing.station_yard import (
    StopShape,
    YardStop,
    default_shapes,
    plan_yard,
)
from autodrive_editor.editing.yard_road import yard_road
from autodrive_editor.file_io.savegame_stations import Stop, StopKind
from autodrive_editor.model.autodrive_data import REGULAR_FLAG, SUBPRIO_FLAG
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


def _out(piece, index):
    return sum(1 for source, _, _ in piece.connections if source == index)
