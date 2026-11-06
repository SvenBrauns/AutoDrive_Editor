import math

import pytest
from road_lane_helpers import HALF_GAP, _along, junction, lane, roundabout

from autodrive_editor.editing.road_graph import build_road_graph
from autodrive_editor.editing.road_network import RoadOptions, build_road_network
from autodrive_editor.model.connections import ConnectionType


def network_of(lanes, **options):
    return build_road_network(build_road_graph(lanes), RoadOptions(**options)).piece


def successors(piece):
    after = {i: set() for i in range(len(piece.points))}
    for a, b, kind in piece.connections:
        after[a].add(b)
        if kind == ConnectionType.DUAL:
            after[b].add(a)
    return after


def nearest(piece, x, z):
    return min(range(len(piece.points)), key=lambda i: math.dist((x, z), piece.points[i][::2]))


def reaches(piece, start, goal):
    after, seen, todo = successors(piece), {start}, [start]
    while todo:
        for n in after[todo.pop()]:
            if n not in seen:
                seen.add(n)
                todo.append(n)
    return goal in seen


def test_two_way_road_becomes_two_lanes_at_the_gap_on_the_map_sides():
    piece = network_of([lane((0, 2), (100, 2)), lane((100, -2), (0, -2))], gap=6.0)

    zs = sorted({round(p[2], 6) for p in piece.points})
    assert zs == pytest.approx([-3.0, 3.0])
    east = nearest(piece, 0, 3)
    assert reaches(piece, east, nearest(piece, 100, 3))
    assert not reaches(piece, nearest(piece, 100, 3), east)
    assert reaches(piece, nearest(piece, 100, -3), nearest(piece, 0, -3))
    assert all(
        math.dist(piece.points[a], piece.points[b]) <= 12.0 + 1e-6 for a, b, _ in piece.connections
    )


def test_two_way_style_is_one_two_way_lane_on_the_centre_line():
    piece = network_of([lane((0, 2), (100, 2)), lane((100, -2), (0, -2))], two_way=True)

    assert all(p[2] == pytest.approx(0) for p in piece.points)
    assert {kind for _, _, kind in piece.connections} == {ConnectionType.DUAL}


def test_heights_come_from_the_map_lanes():
    piece = network_of([lane((0, 0, 2), (100, 20, 2)), lane((100, 20, -2), (0, 0, -2))], gap=4.0)

    assert all(p[1] == pytest.approx(p[0] / 5) for p in piece.points)


def test_lane_goes_on_where_the_road_turns_one_way():
    piece = network_of([lane((0, 2), (200, 2)), lane((100, -2), (0, -2))])

    assert reaches(piece, nearest(piece, 0, 2), nearest(piece, 200, 2))


def arm_ends(angles):
    """Per arm, the far end of the lane into the junction and of the lane out of it (left-hand
    traffic as in the helpers)."""
    return {a: (_along(a, 100, HALF_GAP), _along(a, 100, -HALF_GAP)) for a in angles}


@pytest.mark.parametrize("two_way", [False, True])
@pytest.mark.parametrize(
    "angles", [(0, 90, 180), (0, 90, 180, 270), (90, 210, 330)], ids=["T", "cross", "Y"]
)
def test_every_move_through_a_junction_is_possible(angles, two_way):
    piece = network_of(junction(angles), two_way=two_way)

    ends = arm_ends(angles)
    for a in angles:
        for b in angles:
            if a != b:
                start, goal = nearest(piece, *ends[a][0]), nearest(piece, *ends[b][1])
                assert reaches(piece, start, goal), (a, b)


def test_every_exit_of_a_roundabout_is_reached_from_every_entry():
    angles = (0, 90, 180, 270)
    piece = network_of(roundabout(angles))

    for a in angles:
        for b in angles:
            start = nearest(piece, *_along(a, 100, -HALF_GAP))
            assert reaches(piece, start, nearest(piece, *_along(b, 100, HALF_GAP))), (a, b)


def test_moves_stay_possible_where_a_lane_swings_out_before_the_junction():
    # The lane into the junction from the west swings 14 m out over its last 30 m, so the road
    # stops being two-way there; the turn lanes start where it ends.
    old_end, new_end = _along(180, 10, HALF_GAP), _along(180, 10, 14)
    lanes = []
    for traffic_lane in junction((0, 90, 180)):
        points = [(p[0], p[2]) for p in traffic_lane.points]
        if points[-1] == old_end:
            points = [points[0], _along(180, 40, HALF_GAP), new_end]
        if points[0] == old_end:
            points[0] = new_end
        lanes.append(lane(*points))
    piece = network_of(lanes)

    ends = arm_ends((0, 90, 180))
    for a in (0, 90, 180):
        for b in (0, 90, 180):
            if a != b:
                start, goal = nearest(piece, *ends[a][0]), nearest(piece, *ends[b][1])
                assert reaches(piece, start, goal), (a, b)
