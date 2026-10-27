import pytest

from autodrive_editor.model.autodrive_data import AutoDriveData, NodeData
from autodrive_editor.network_check.checks import (
    HEIGHT,
    OUTSIDE,
    OVERLAP,
    CheckResults,
    HeightProblem,
    check_network,
    find_height_problems,
    find_nodes_outside_map,
    find_overlapping_nodes,
    problem_node_ids,
)


def make_data(*positions):
    """Nodes 1, 2, … at the given (x, y, z) positions."""

    autodrive_data = AutoDriveData()

    for node_id, (x, y, z) in enumerate(positions, start=1):
        autodrive_data.add_node(NodeData(node_id, x, y, z))

    return autodrive_data


def test_nodes_within_the_tolerance_form_a_group():
    data = make_data((0, 0, 0), (0.05, 0, 0), (50, 0, 0), (50, 0, 0.08))

    assert find_overlapping_nodes(data, 0.1) == [[1, 2], [3, 4]]


def test_nodes_further_apart_than_the_tolerance_are_not_reported():
    data = make_data((0, 0, 0), (0.2, 0, 0), (0, 0, 0.2))

    assert find_overlapping_nodes(data, 0.1) == []


def test_height_counts_for_the_distance():
    """A node on a bridge above another node is not a duplicate."""

    data = make_data((0, 0, 0), (0, 6, 0), (0, 6.05, 0))

    assert find_overlapping_nodes(data, 0.1) == [[2, 3]]


def test_nodes_in_neighboring_grid_cells_are_found():
    data = make_data((0.099, 0, 0), (0.101, 0, 0), (0.0, 0, -0.001))

    assert find_overlapping_nodes(data, 0.1) == [[1, 2, 3]]


def test_chained_nodes_form_one_group():
    data = make_data((0, 0, 0), (0.08, 0, 0), (0.16, 0, 0))

    assert find_overlapping_nodes(data, 0.1) == [[1, 2, 3]]


def test_tolerance_must_be_positive():
    with pytest.raises(ValueError):
        find_overlapping_nodes(make_data(), 0)


def test_nodes_outside_the_map():
    """Map scale 1 is 2048 m wide, from -1024 to 1024."""

    data = make_data((0, 0, 0), (1024, 0, -1024), (1024.5, 0, 0), (0, 0, -2000))

    assert find_nodes_outside_map(data, 1) == [3, 4]
    assert find_nodes_outside_map(data, 4) == []


def test_heights_too_far_from_the_terrain():
    data = make_data((0, 10, 0), (5, 14, 0), (10, 30, 0), (2000, 0, 0))

    def terrain_height_at(x, z):
        return None if x > 1024 else 10.0

    assert find_height_problems(data, terrain_height_at, 5.0) == [HeightProblem(3, 30, 10.0)]


def test_check_network_without_heightmap_skips_heights():
    data = make_data((0, 0, 0), (0, 0, 0), (2000, 0, 0))

    results = check_network(data, 1, None, 0.1, 5.0)

    assert results == CheckResults([[1, 2]], [3], None)
    assert results.problem_count == 2


def test_switched_off_checks_report_nothing():
    data = make_data((0, 50, 0), (0, 50, 0), (2000, 0, 0))

    results = check_network(data, 1, lambda x, z: 0.0, 0.1, 5.0, checks={OUTSIDE})

    assert results == CheckResults([], [3], [])


def test_entries_round_trip():
    results = CheckResults([[1, 2]], [3], [HeightProblem(4, 1.0, 9.0)])

    assert results.entries() == [
        (OVERLAP, [1, 2]),
        (OUTSIDE, 3),
        (HEIGHT, HeightProblem(4, 1.0, 9.0)),
    ]
    assert CheckResults.from_entries(results.entries() * 2) == results
    assert [problem_node_ids(*entry) for entry in results.entries()] == [[1, 2], [3], [4]]


def test_check_network_with_heightmap():
    data = make_data((0, 50, 0))

    results = check_network(data, 1, lambda x, z: 0.0, 0.1, 5.0)

    assert results.height_problems == [HeightProblem(1, 50, 0.0)]
    assert results.problem_count == 1
