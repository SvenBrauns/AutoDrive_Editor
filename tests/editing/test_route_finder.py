import math
from itertools import pairwise

import pytest
from costmap_helpers import GRASS, ROAD, make_costmap

from autodrive_editor.editing.route_finder import (
    SWERVE_COST,
    Grid,
    RouteFinder,
    RouteRequest,
    Vehicle,
    _Node,
    _Search,
    cell_cost,
)
from autodrive_editor.file_io.navigation_costmap import NavigationCostmap

VEHICLE = Vehicle(turning_radius=8, width=3, margin=0.5)


def find(costmap, request):
    route = RouteFinder(costmap, VEHICLE).find(request)

    return None if route is None else route.points


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
    route = find(make_costmap(), RouteRequest(((-40, 0), (40, 0)), (0.0,), (0.0,)))

    assert route[0] == (-40, 0)
    assert route[-1] == pytest.approx((40, 0))
    assert all(abs(z) < 0.5 for _, z in route)


def test_route_goes_around_a_wall_and_keeps_its_distance():
    wall = (-5, -60, 5, 40)
    route = find(make_costmap(blocked=[wall]), RouteRequest(((-30, 0), (30, 0)), (0.0,), (0.0,)))

    assert route is not None
    # Half the width plus the margin (2 m) away from the wall, less up to about a cell, as the
    # distance is kept per 1 m cell (most at the wall's corners).
    for x, z in route:
        distance = math.hypot(max(-5 - x, 0, x - 5), max(-60 - z, 0, z - 40))
        assert distance > 0.9


def test_route_turns_no_tighter_than_the_radius():
    route = find(make_costmap(), RouteRequest(((0, 0), (0, 20)), (0.0,), (math.pi,)))

    assert route[-1] == pytest.approx((0, 20))
    assert max_turn(route) <= 1 / VEHICLE.turning_radius + 0.02


def test_turning_radius_of_the_request_replaces_the_vehicles():
    request = RouteRequest(((0, 0), (0, 14)), (0.0,), (math.pi,), turning_radius=5)
    route = find(make_costmap(), request)

    assert route[-1] == pytest.approx((0, 14))
    assert max_turn(route) <= 1 / 5 + 0.02
    # The U-turn is narrower than the vehicle's radius would allow.
    assert max(x for x, _ in route) < VEHICLE.turning_radius


CLOSED_AREA = [(20, -20, 22, 20), (40, -20, 42, 20), (20, -22, 42, -20), (20, 20, 42, 22)]


def test_route_into_a_closed_area_crosses_the_wall_and_marks_it():
    request = RouteRequest(((-40, 0), (31, 0)))
    route = RouteFinder(make_costmap(blocked=CLOSED_AREA), VEHICLE).find(request)

    assert not route.is_clear
    crossing = [
        point for point, blocked in zip(route.points, route.blocked, strict=True) if blocked
    ]
    assert crossing
    assert all(20 <= x < 22 for x, _ in crossing)


def test_route_around_an_obstacle_is_clear():
    wall = (-5, -60, 5, 40)
    request = RouteRequest(((-30, 0), (30, 0)), (0.0,), (0.0,))

    assert RouteFinder(make_costmap(blocked=[wall]), VEHICLE).find(request).is_clear


def test_route_passes_the_waypoints_in_order():
    waypoints = ((-40, 0), (0, 30), (40, 0))
    route = RouteFinder(make_costmap(), VEHICLE).find(RouteRequest(waypoints, (0.0,)))

    for index, waypoint in zip(route.waypoint_indices, waypoints, strict=True):
        assert route.points[index] == pytest.approx(waypoint)
    assert route.waypoint_indices == sorted(route.waypoint_indices)
    assert max_turn(route.points) <= 1 / VEHICLE.turning_radius + 0.02


def test_heading_at_a_waypoint_suits_the_next_leg():
    # A dead-end pocket open to the east with room for one turn: the route has to turn while
    # passing the waypoint to get out again.
    pocket = [(-20, -27, 30, -25), (-20, 25, 30, 27), (-22, -27, -20, 27)]
    waypoints = ((60, 0), (0, 0), (60, 40))
    request = RouteRequest(waypoints, (math.pi,))
    route = RouteFinder(make_costmap(blocked=pocket), VEHICLE).find(request)

    assert route.is_clear


def test_start_under_a_roof_can_be_left():
    roof = (-50, -5, -30, 5)
    route = find(make_costmap(blocked=[roof]), RouteRequest(((-36, 0), (30, 0)), (0.0,), (0.0,)))

    assert route is not None


def test_roads_are_preferred_over_grass():
    # Grass everywhere except a road 20 m to the side.
    costmap = make_costmap(value=GRASS)
    cells = bytearray(costmap.cells)
    for z in range(18, 23):
        for x in range(-100, 100):
            cells[(z + 100) * 200 + x + 100] = 51
    costmap = type(costmap)(200, 200, bytes(cells))

    route = find(costmap, RouteRequest(((-60, 0), (60, 0)), (0.0,), (0.0,)))

    assert max(z for _, z in route) > 17


def test_planned_lanes_against_the_direction_are_avoided_where_there_is_room():
    lane = ((60.0, 0.0), (-60.0, 0.0))
    request = RouteRequest(((-60, 0), (60, 0)), (0.0,), (0.0,), lanes=(lane,))
    route = find(make_costmap(), request)

    # The way back keeps beside the lane in the middle part.
    assert max(abs(z) for _, z in route) > VEHICLE.width


def test_planned_lanes_in_the_direction_are_followed():
    lane = ((-60.0, 5.0), (60.0, 5.0))
    request = RouteRequest(((-60, 0), (60, 0)), (0.0,), (0.0,), lanes=(lane,))
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


def test_route_passes_a_gate_narrower_than_the_safety_distance():
    # A fence across the map with a 3 m opening, like a 4 m gate on the map.
    fence = [(-1, -100, 1, -1), (-1, 2, 1, 100)]
    route = find(make_costmap(blocked=fence), RouteRequest(((-30, 0), (30, 0)), (0.0,), (0.0,)))

    assert route is not None


def test_without_headings_the_route_runs_straight():
    route = find(make_costmap(), RouteRequest(((0, 0), (30, 17))))

    # On the line from start to goal.
    assert all(abs(x * 17 - z * 30) / math.hypot(30, 17) < 0.3 for x, z in route)


def test_debug_log_tells_that_the_route_crosses_blocked_cells(caplog):
    with caplog.at_level("DEBUG", logger="autodrive_editor.editing.route_finder"):
        find(make_costmap(blocked=CLOSED_AREA), RouteRequest(((-40, 0), (31, 0))))

    assert "Route search through (-40.0, 0.0), (31.0, 0.0)" in caplog.text
    assert "crosses blocked cells" in caplog.text


def test_a_waypoint_in_a_closed_area_is_still_passed_and_the_crossing_marked(monkeypatch):
    # Few steps, so the search gets stuck before the goal and continues in direct curves.
    monkeypatch.setattr("autodrive_editor.editing.route_finder.MAX_EXPANSIONS", 300)
    waypoints = ((-40, 0), (31, 0), (60, 40))
    route = RouteFinder(make_costmap(blocked=CLOSED_AREA), VEHICLE).find(RouteRequest(waypoints))

    for index, waypoint in zip(route.waypoint_indices, waypoints, strict=True):
        assert route.points[index] == pytest.approx(waypoint)
    assert not route.is_clear


def swerves(points):
    """Number of changes from a left to a right turn or back along the points."""

    headings = [math.atan2(b[1] - a[1], b[0] - a[0]) for a, b in pairwise(points)]
    turns = [math.remainder(h2 - h1, math.tau) for h1, h2 in pairwise(headings)]
    signs = [turn > 0 for turn in turns if abs(turn) > 0.004]

    return sum(1 for a, b in pairwise(signs) if a != b)


def test_changing_from_a_left_to_a_right_turn_costs_extra():
    search = _Search(RouteFinder(make_costmap(), VEHICLE), RouteRequest(((0, 0), (40, 0))), 60)
    left = 1 / VEHICLE.turning_radius
    node = _Node((0.0, 0.0, 0.0), 0.0, None, curvature=left)

    swerved = search._step(node, -left).cost
    kept = search._step(node, left).cost

    assert swerved == pytest.approx(kept + SWERVE_COST)


def test_diagonal_route_is_straightened():
    request = RouteRequest(((-60, -40), (60, 40)), (0.0,), (0.0,))
    route = find(make_costmap(), request)

    # One turn left towards the goal, one right onto the goal heading, straight between.
    assert swerves(route) <= 1
    assert route[-1] == pytest.approx((60, 40))
    assert max_turn(route) <= 1 / VEHICLE.turning_radius + 0.02


def test_straightened_route_does_not_cut_a_road_corner_across_grass():
    # An L-shaped road, 11 m wide, on grass.
    cells = bytearray(make_costmap(value=GRASS).cells)
    for x1, z1, x2, z2 in ((-80, -5, 6, 6), (-5, -5, 6, 80)):
        for z in range(z1, z2):
            for x in range(x1, x2):
                cells[(z + 100) * 200 + x + 100] = ROAD
    costmap = NavigationCostmap(200, 200, bytes(cells))

    route = find(costmap, RouteRequest(((-70, 0), (0, 70)), (0.0,), (math.pi / 2,)))

    assert all(costmap.value_at(x, z) == ROAD for x, z in route)


def test_shortcut_does_not_move_onto_worse_ground():
    # A detour on the road at z = 10 around a grass patch at z = 0, given a high cost so only
    # the kind of ground can refuse the straight shortcut.
    def shortcut(costmap):
        search = _Search(RouteFinder(costmap, VEHICLE), RouteRequest(((-20, 0), (20, 0))), 60)
        start = _Node((-20.0, 0.0, 0.0), 0.0, None, [(-20.0, 0.0)])
        detour = [(-20.0, 10.0), (20.0, 10.0), (20.0, 0.0)]
        end = _Node((20.0, 0.0, 0.0), 1000.0, start, detour)
        worst = [search._worst_ground(node.points) for node in (start, end)]

        return search._shortcut([start, end], [0.0, 60.0], worst, 0, 1)

    grass = bytearray(make_costmap().cells)
    for z in range(-2, 2):
        for x in range(-2, 2):
            grass[(z + 100) * 200 + x + 100] = GRASS

    assert shortcut(make_costmap()) is not None
    assert shortcut(NavigationCostmap(200, 200, bytes(grass))) is None


def test_route_keeps_to_the_line_between_waypoints_after_a_corner():
    waypoints = ((-50, 0), (0, 0), (0, 60))
    route = RouteFinder(make_costmap(), VEHICLE).find(RouteRequest(waypoints))
    corner, goal = route.waypoint_indices[1:]
    after_curve = [x for x, z in route.points[corner:goal] if z > 3 * VEHICLE.turning_radius]

    assert after_curve
    assert max(abs(x) for x in after_curve) < 1.0
