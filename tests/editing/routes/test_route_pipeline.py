import math

import pytest

from autodrive_editor.editing.routes.route_geometry import fillet
from autodrive_editor.editing.routes.route_pipeline import bisector, direct_corners


def test_an_inner_waypoint_is_passed_halfway_between_its_lines():
    assert bisector((-50, 0), (0, 0), (0, 60)) == pytest.approx(math.pi / 4)


def test_without_headings_the_direct_way_is_a_straight_line():
    assert direct_corners((0, 0), None, (30, 17), None, 6) == [[(0, 0), (30, 17)]]


@pytest.mark.parametrize(
    ("start_heading", "goal_heading"), [(0.0, None), (None, math.pi / 2), (0.0, math.pi / 2)]
)
def test_direct_ways_keep_the_given_headings(start_heading, goal_heading):
    ways = direct_corners((0, 0), start_heading, (20, 30), goal_heading, 6)

    assert ways
    for corners in ways:
        pieces = fillet(corners, 6)
        assert pieces[-1].end[:2] == pytest.approx((20, 30))
        if start_heading is not None:
            assert pieces[0].start[2] == pytest.approx(start_heading)
        if goal_heading is not None:
            assert pieces[-1].end[2] == pytest.approx(goal_heading)
