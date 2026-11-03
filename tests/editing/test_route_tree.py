from test_route_nodes import data_with, line

from autodrive_editor.editing.route_finder import Route
from autodrive_editor.editing.route_tree import (
    TreeNodes,
    TreeRoute,
    runs_beside,
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
