import math
from itertools import pairwise

import pytest

from autodrive_editor.editing.route_geometry import fillet, sample


def _assert_smooth(pieces):
    for piece, following in pairwise(pieces):
        x, z, heading = piece.end
        assert (x, z) == pytest.approx(following.start[:2], abs=1e-6)
        assert math.remainder(heading - following.start[2], math.tau) == pytest.approx(0, abs=1e-9)


def test_a_line_without_corners_is_one_straight_piece():
    pieces = fillet([(0, 0), (5, 0), (20, 0)], 6)

    assert len(pieces) == 1
    assert pieces[0].length == pytest.approx(20)
    assert pieces[0].curvature == 0


def test_a_right_angle_is_rounded_with_the_radius():
    pieces = fillet([(0, 0), (30, 0), (30, 30)], 6)

    assert [piece.curvature for piece in pieces] == pytest.approx([0, 1 / 6, 0])
    assert pieces[1].start[:2] == pytest.approx((24, 0))
    assert sum(piece.length for piece in pieces) == pytest.approx(2 * 24 + math.pi * 3)
    _assert_smooth(pieces)
    assert pieces[-1].end == pytest.approx((30, 30, math.pi / 2))


def test_corners_too_close_turning_the_same_way_become_one():
    # Two 45° left turns 2 m apart: no room for two arcs of 6 m, room for one 90° arc.
    pieces = fillet([(0, 0), (20, 0), (22, 2), (22, 25)], 6)

    assert [piece.curvature for piece in pieces] == pytest.approx([0, 1 / 6, 0])
    assert pieces[1].start[:2] == pytest.approx((16, 0))
    _assert_smooth(pieces)
    assert pieces[-1].end == pytest.approx((22, 25, math.pi / 2))


def test_an_s_bend_too_tight_for_the_radius_fails():
    assert fillet([(0, 0), (20, 0), (22, 2), (40, 2)], 6) is None


def test_arcs_need_room_up_to_the_ends():
    assert fillet([(0, 0), (3, 0), (3, 30)], 6) is None


def test_turning_back_fails():
    assert fillet([(0, 0), (20, 0), (5, 0)], 6) is None


def test_sampled_points_are_close_together_and_end_exactly():
    points = sample(fillet([(0, 0), (30, 0), (30, 30)], 6), 0.5)

    assert points[0] == (0, 0)
    assert points[-1] == pytest.approx((30, 30))
    assert max(math.dist(a, b) for a, b in pairwise(points)) <= 0.5 + 1e-9
    # On the arc, every point is one radius from its centre.
    on_arc = [point for point in points if point[0] > 24 and point[1] < 6]
    assert on_arc
    assert all(math.dist(point, (24, 6)) == pytest.approx(6) for point in on_arc)
