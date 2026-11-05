import math
from itertools import pairwise

import pytest

from autodrive_editor.editing.yard_road import length, road_points, yard_road


def test_through_road_runs_from_first_to_last_corner_with_rounded_corner():
    road = yard_road([(0, 0), (50, 0), (50, 50)], radius=6.0)

    assert not road.loop and road.stem == []
    assert road.road[0] == pytest.approx((0, 0)) and road.road[-1] == pytest.approx((50, 50))
    # The arc cuts the corner: shorter than the corner path by 2r - r·π/2.
    assert length(road.road) == pytest.approx(100 - 12 + 3 * math.pi, abs=0.01)


def test_loop_has_two_way_stem_and_ring_in_click_order():
    corners = [(0, 0), (20, 0), (60, 0), (60, 40), (20, 40), (20, 0)]
    road = yard_road(corners, radius=6.0, closes_at=1)

    assert road.loop
    assert road.stem[0] == pytest.approx((0, 0)) and road.stem[-1] == pytest.approx((20, 0))
    assert road.road[0] == pytest.approx((20, 0)) and road.road[-1] == pytest.approx((20, 0))
    # Clicked counterclockwise (x right, z down on the map): first along the stem's line.
    assert road.road[1][0] > 20


def test_ring_at_first_corner_has_no_stem():
    road = yard_road([(0, 0), (40, 0), (40, 40), (0, 40), (0, 0)], radius=6.0, closes_at=0)

    assert road.loop and road.stem == []


def test_road_that_cannot_be_rounded_or_is_too_short_is_none():
    assert yard_road([(0, 0)], radius=6.0) is None
    assert yard_road([(0, 0), (40, 0), (0, 0)], radius=6.0, closes_at=0) is None
    # A corner that turns back cannot be rounded.
    assert yard_road([(0, 0), (40, 0), (0, 1)], radius=6.0) is None


def test_road_points_have_a_node_at_each_fixed_distance():
    line = yard_road([(0, 0), (100, 0)], radius=6.0).road
    points = road_points(line, spacing=12.0, fixed=[30.0, 55.5])

    assert points[0] == pytest.approx((0, 0)) and points[-1] == pytest.approx((100, 0))
    assert any(p == pytest.approx((30, 0)) for p in points)
    assert any(p == pytest.approx((55.5, 0)) for p in points)
    assert max(math.dist(a, b) for a, b in pairwise(points)) <= 12.0 + 1e-6


def test_fixed_distances_close_together_or_to_an_end_share_a_node():
    road = yard_road([(0, 0), (50, 0), (50, 50)], radius=6.0).road
    points = road_points(road, 12.0, [0.3, 20.0, 20.25, 20.6, length(road) - 0.4])

    gaps = [math.dist(a, b) for a, b in pairwise(points)]
    assert min(gaps) >= 0.5
    assert any(p == pytest.approx((20, 0)) for p in points)
