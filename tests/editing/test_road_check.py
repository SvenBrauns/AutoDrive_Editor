import math

import pytest
from road_lane_helpers import _along, junction, lane, roundabout

from autodrive_editor.editing.edit_history import EditHistory
from autodrive_editor.editing.planned_piece import push_piece
from autodrive_editor.editing.road_check import check_road_network
from autodrive_editor.editing.road_existing import fit_to_existing
from autodrive_editor.editing.road_graph import build_road_graph
from autodrive_editor.editing.road_network import RoadOptions, build_road_network
from autodrive_editor.file_io.navigation_costmap import BLOCKED_VALUE, NavigationCostmap
from autodrive_editor.model.autodrive_data import AutoDriveData

T = junction((0, 90, 180))


def checked(lanes, network=None, data=None, costmap=None, **options):
    graph = build_road_graph(lanes)
    network = network or build_road_network(graph, RoadOptions(**options))
    before = len(network.listed)
    result = check_road_network(network, graph, data or AutoDriveData(), costmap)
    return result.listed[before:]


@pytest.mark.parametrize(
    "lanes, two_way",
    [
        (T, False),
        (T, True),
        (junction((0, 90, 180, 270)), False),
        (roundabout((0, 120, 240)), False),
    ],
    ids=["box", "two-way", "cross", "roundabout"],
)
def test_a_complete_network_has_no_failures(lanes, two_way):
    assert checked(lanes, two_way=two_way) == []


def test_a_short_lane_from_a_road_end_is_no_missing_move():
    end = _along(90, 10, -2.0)
    assert checked([*T, lane((end[0] + 12, end[1]), end)]) == []


def test_turns_through_a_missing_centre_are_listed_once_at_the_junction():
    network = build_road_network(build_road_graph(T))
    piece = network.piece
    centre = min(range(len(piece.points)), key=lambda i: math.dist(piece.points[i][::2], (0, 0)))
    piece.connections = [c for c in piece.connections if centre not in c[:2]]

    (point, _), *rest = checked(T, network)
    assert rest == [] and math.dist(point[::2], (0, 0)) < 15


def test_a_broken_lane_gives_a_dead_end_and_a_lane_never_reached():
    network = build_road_network(build_road_graph(T))
    piece = network.piece
    a, b, _ = next(c for c in piece.connections if -80 < piece.points[c[0]][0] < -30)
    piece.connections.remove((a, b, _))

    points = [p for p, _ in checked(T, network) if p[0] < -20]
    assert sorted(points) == sorted([piece.points[a], piece.points[b]])


def test_moves_through_a_kept_existing_junction_count():
    data = AutoDriveData()
    push_piece(EditHistory(), data, build_road_network(build_road_graph(T)).piece, "Create")
    network = fit_to_existing(build_road_network(build_road_graph(T)), data, False, 5.5)

    assert checked(T, network, data) == []


def test_new_connections_over_blocked_cells_are_listed_every_20_m():
    size = 400
    cells = bytearray(size * size)
    for row in range(size):  # blocked from x = -60 to -10, across the whole map
        for column in range(size // 2 - 60, size // 2 - 10):
            cells[row * size + column] = BLOCKED_VALUE
    costmap = NavigationCostmap(size, size, bytes(cells))

    listed = checked(T, costmap=costmap)
    assert listed and all(-62 <= p[0] <= -8 for p, _ in listed)
    assert all(math.dist(p, q) > 20 for (p, _), (q, _) in zip(listed, listed[1:], strict=False))
