import math

import pytest
from test_route_nodes import data_with, line

from autodrive_editor.editing.route_finder import Route
from autodrive_editor.editing.route_tree import (
    TreeNodes,
    TreeRoute,
    runs_beside,
    shared_headings,
    tree_chains,
    tree_connections,
)
from autodrive_editor.model.connections import CONNECTION_STATES, ConnectionType

REGULAR = CONNECTION_STATES[ConnectionType.REGULAR]
DUAL = CONNECTION_STATES[ConnectionType.DUAL]


def straight(start, end):
    points = [start, *line(start, end)]

    return Route(points, [0, len(points) - 1], [False] * len(points))


def test_a_route_running_close_beside_another_without_sharing_it():
    route = straight((0, 0), (40, 0))

    assert runs_beside(straight((0, 4), (40, 4)), route)
    assert runs_beside(straight((40, 4), (0, 4)), route)
    # Shared, too far away, too short or crossing.
    assert not runs_beside(straight((0, 0.5), (40, 0.5)), route)
    assert not runs_beside(straight((0, 12), (40, 12)), route)
    assert not runs_beside(straight((0, 4), (15, 4)), route)
    assert not runs_beside(straight((20, -20), (20, 20)), route)


def test_a_later_route_from_the_same_start_shares_the_new_nodes_of_the_one_before():
    nodes = TreeNodes({0: 1, 1: 2, 2: 3}, {1: (0, 0), 2: (40, 0), 3: (60, 0)}, (), 5.0, 3.5, 10)
    routes = [
        TreeRoute((0, 1), straight((0, 0), (40, 0))),
        TreeRoute((0, 2), straight((0, 0), (60, 0))),
    ]

    tree = tree_chains(routes, nodes)

    first, second = tree.chains
    assert first[0] == 1 and first[-1] == 2 and len(first) > 3
    assert second[: len(first) - 1] == first[:-1]
    assert set(tree.new_positions) == {n for n in first + second if n >= 10}


def test_connections_of_several_chains_are_added_once_and_dual_when_driven_both_ways():
    data = data_with((1, 0, 0), (2, 10, 0), (3, 20, 0))

    connections = tree_connections(data, [[1, 2, 3], [1, 2], [3, 2]])

    assert connections == [(1, 2, REGULAR), (2, 3, DUAL)]


def test_a_waypoint_several_routes_pass_gets_one_heading_halfway_between_theirs():
    points = {0: (0, 0), 1: (10, 0), 2: (20, 0), 3: (10, 10)}

    # Straight on to 2 (0°) and a right angle to 3 (45° alone): halfway is 22.5°.
    headings = shared_headings([(0, 1, 2), (0, 1, 3), (0, 2)], points)

    assert headings == {1: pytest.approx(math.radians(22.5))}


def through(start, *legs):
    """A route along straight pieces; each leg is the list of its corners after its start."""

    points, indices = [start], [0]

    for leg in legs:
        for corner in leg:
            points += line(points[-1], corner)

        indices.append(len(points) - 1)

    return Route(points, indices, [False] * len(points))


@pytest.mark.parametrize(
    "second_leg",
    [
        # The same line as the first route, but its end lies a rounding error past the
        # waypoint, so it is nearer to the first route's next leg.
        [(-12.71, -13.71)],
        [(-5, -8), (-12.7, -13.7)],  # Its search ran up to 2 m beside the first route.
    ],
)
def test_routes_through_the_same_waypoints_share_the_nodes_of_that_leg(second_leg):
    # Start 0, shared waypoint 1, ends 2 and 3. Both routes leave the waypoint in the same
    # direction and split later.
    positions = {1: (0, 0), 2: (-12.7, -13.7), 3: (-6, -26.4), 4: (-19.1, -39.2)}
    nodes = TreeNodes({0: 1, 1: 2, 2: 3, 3: 4}, positions, (), 5.0, 3.5, 10)
    routes = [
        TreeRoute((0, 1, 2), through((0, 0), [(-12.7, -13.7)], [(-17, -18.3), (-6, -26.4)])),
        TreeRoute((0, 1, 3), through((0, 0), second_leg, [(-19.1, -39.2)])),
    ]

    first, second = tree_chains(routes, nodes).chains

    assert second[: second.index(2) + 1] == first[: first.index(2) + 1]
