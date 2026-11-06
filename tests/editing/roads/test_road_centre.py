import pytest
from road_lane_helpers import junction, lane, roundabout, two_way_circle

from autodrive_editor.editing.roads.road_centre import road_pieces
from autodrive_editor.editing.roads.road_graph import build_road_graph


def pieces_of(lanes):
    return road_pieces(build_road_graph(lanes))


def test_opposite_lanes_make_one_two_way_road_on_the_centre_line():
    (piece,) = pieces_of([lane((0, 2), (100, 2)), lane((100, -2), (0, -2))])

    assert piece.two_way
    assert piece.points[0] == pytest.approx((0, 0, 0)) and piece.points[-1] == pytest.approx(
        (100, 0, 0)
    )
    assert all(p[2] == pytest.approx(0) for p in piece.points)
    assert piece.start is None and piece.end is None


def test_lane_alone_stays_one_way():
    (piece,) = pieces_of([lane((0, 0), (100, 0))])

    assert not piece.two_way and piece.points[-1] == (100, 0, 0)


def test_lanes_too_far_apart_stay_one_way():
    pieces = pieces_of([lane((0, 10), (100, 10)), lane((100, -10), (0, -10))])

    assert len(pieces) == 2 and not any(p.two_way for p in pieces)


@pytest.mark.parametrize(
    "angles", [(0, 90, 180), (0, 90, 180, 270), (90, 210, 330)], ids=["T", "cross", "Y"]
)
def test_every_arm_is_a_two_way_road_into_the_junction(angles):
    pieces = pieces_of(junction(angles))

    assert len(pieces) == len(angles)
    assert all(p.two_way and {p.start, p.end} == {0, None} for p in pieces)


def test_slip_road_stays_one_way_beside_the_two_way_road():
    pieces = pieces_of(
        [
            lane((0, 2), (100, 2)),
            lane((100, 2), (200, 2)),
            lane((100, 2), (150, 30), (200, 60)),
            lane((200, -2), (0, -2)),
        ]
    )

    two_way = [p for p in pieces if p.two_way]
    one_way = [p for p in pieces if not p.two_way]
    assert len(two_way) == 2 and all(0 in (p.start, p.end) for p in two_way)
    assert len(one_way) == 1 and one_way[0].start == 0 and one_way[0].points[-1] == (200, 0, 60)


def test_roundabout_arms_are_two_way_roads_and_the_ring_is_left_to_the_junction():
    pieces = pieces_of(roundabout((0, 90, 180, 270)))

    assert sum(p.two_way for p in pieces) == 4
    assert all(0 in (p.start, p.end) for p in pieces)


def test_loops_crossing_are_cut_at_the_crossings():
    pieces = pieces_of([*two_way_circle((0, 0), 200), *two_way_circle((300, 0), 200)])

    assert len(pieces) == 4
    assert all(p.two_way and {p.start, p.end} == {0, 1} for p in pieces)


def test_road_is_two_way_only_where_both_lanes_find_each_other():
    # The westbound lane turns away at x = 60; the eastbound lane must not lose a bit there.
    pieces = pieces_of([lane((0, -2), (100, -2)), lane((100, 2), (60, 2), (40, 22), (0, 22))])

    (two_way,) = [p for p in pieces if p.two_way]
    (eastbound,) = [p for p in pieces if not p.two_way and p.forward == two_way.forward]
    assert eastbound.points[-1][0] >= two_way.points[0][0]
