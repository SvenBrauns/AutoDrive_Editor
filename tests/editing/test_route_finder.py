import math
from itertools import pairwise

import pytest
from costmap_helpers import GRASS, make_costmap

from autodrive_editor.editing.route_finder import (
    Grid,
    RouteFinder,
    RouteRequest,
    Vehicle,
    cell_cost,
)

VEHICLE = Vehicle(turning_radius=8, width=3, margin=0.5)


def find(costmap, request):
    return RouteFinder(costmap, VEHICLE).find(request)


def max_turn(points):
    """Largest heading change per metre along the points."""

    pieces = list(pairwise(points))
    headings = [math.atan2(b[1] - a[1], b[0] - a[0]) for a, b in pieces]
    lengths = [math.dist(a, b) for a, b in pieces]

    return max(
        abs(math.remainder(h2 - h1, math.tau)) / ((l1 + l2) / 2)
        for (h1, h2), (l1, l2) in zip(pairwise(headings), pairwise(lengths), strict=True)
    )


def test_straight_route_on_open_ground():
    route = find(make_costmap(), RouteRequest((-40, 0), (40, 0), (0.0,), (0.0,)))

    assert route[0] == (-40, 0)
    assert route[-1] == pytest.approx((40, 0))
    assert all(abs(z) < 0.5 for _, z in route)


def test_route_goes_around_a_wall_and_keeps_its_distance():
    wall = (-5, -60, 5, 40)
    route = find(make_costmap(blocked=[wall]), RouteRequest((-30, 0), (30, 0), (0.0,), (0.0,)))

    assert route is not None
    # Half the width plus the margin (2 m) away from the wall, less up to a cell.
    for x, z in route:
        distance = math.hypot(max(-5 - x, 0, x - 5), max(-60 - z, 0, z - 40))
        assert distance > 1.0


def test_route_turns_no_tighter_than_the_radius():
    route = find(make_costmap(), RouteRequest((0, 0), (0, 20), (0.0,), (math.pi,)))

    assert route[-1] == pytest.approx((0, 20))
    assert max_turn(route) <= 1 / VEHICLE.turning_radius + 0.02


def test_no_route_into_a_closed_area():
    walls = [(20, -20, 22, 20), (40, -20, 42, 20), (20, -22, 42, -20), (20, 20, 42, 22)]
    request = RouteRequest((-40, 0), (31, 0))

    assert find(make_costmap(blocked=walls), request) is None


def test_start_under_a_roof_can_be_left():
    roof = (-50, -5, -30, 5)
    route = find(make_costmap(blocked=[roof]), RouteRequest((-36, 0), (30, 0), (0.0,), (0.0,)))

    assert route is not None


def test_roads_are_preferred_over_grass():
    # Grass everywhere except a road 20 m to the side.
    costmap = make_costmap(value=GRASS)
    cells = bytearray(costmap.cells)
    for z in range(18, 23):
        for x in range(-100, 100):
            cells[(z + 100) * 200 + x + 100] = 51
    costmap = type(costmap)(200, 200, bytes(cells))

    route = find(costmap, RouteRequest((-60, 0), (60, 0), (0.0,), (0.0,)))

    assert max(z for _, z in route) > 17


def test_planned_lanes_against_the_direction_are_avoided_where_there_is_room():
    lane = ((60.0, 0.0), (-60.0, 0.0))
    request = RouteRequest((-60, 0), (60, 0), (0.0,), (0.0,), lanes=(lane,))
    route = find(make_costmap(), request)

    # The way back keeps beside the lane in the middle part.
    assert max(abs(z) for _, z in route) > VEHICLE.width


def test_planned_lanes_in_the_direction_are_followed():
    lane = ((-60.0, 5.0), (60.0, 5.0))
    request = RouteRequest((-60, 0), (60, 0), (0.0,), (0.0,), lanes=(lane,))
    route = find(make_costmap(), request)

    on_lane = [point for point in route if abs(point[1] - 5) < 1]
    assert len(on_lane) > len(route) / 2


def test_widened_blocked_cells():
    grid = Grid(make_costmap(20, blocked=[(0, 0, 1, 1)]), (0, 0, 20, 20), 2.0)

    assert grid.blocked[grid.index(0.5, 0.5)]
    assert grid.blocked[grid.index(2.5, 0.5)]
    assert grid.blocked[grid.index(1.5, 1.5)]
    assert not grid.blocked[grid.index(3.5, 0.5)]
    assert not grid.blocked[grid.index(2.5, 2.5)]


def test_cost_by_kind_of_ground():
    assert cell_cost(51) == 1.0
    assert cell_cost(85) == 8.0
    assert cell_cost(119) == 4.0
    assert 4.0 < cell_cost(130) < 8.0
