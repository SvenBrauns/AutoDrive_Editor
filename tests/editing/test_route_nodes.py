import math

import pytest

from autodrive_editor.editing.route_nodes import (
    PlannedLane,
    chain_connections,
    node_headings,
    planned_lanes,
    route_nodes,
)
from autodrive_editor.model.autodrive_data import AutoDriveData, NodeData
from autodrive_editor.model.connections import (
    CONNECTION_STATES,
    ConnectionType,
    write_connection_state,
)

REGULAR = CONNECTION_STATES[ConnectionType.REGULAR]
DUAL = CONNECTION_STATES[ConnectionType.DUAL]


def line(start, end, step=0.5):
    """Points from start to end, `step` apart, without the start."""

    count = round(math.dist(start, end) / step)

    return [
        (start[0] + (end[0] - start[0]) * i / count, start[1] + (end[1] - start[1]) * i / count)
        for i in range(1, count + 1)
    ]


def data_with(*nodes, connections=()):
    data = AutoDriveData()

    for node_id, x, z in nodes:
        data.add_node(NodeData(node_id, x, 0, z))

    for source, target, state in connections:
        write_connection_state(data, source, target, state)

    return data


def test_free_route_gets_evenly_spaced_new_nodes():
    chain = route_nodes(line((0, 0), (20, 0)), 1, 2, {1: (0, 0), 2: (20, 0)}, [], 5.0)

    assert chain[0] == 1 and chain[-1] == 2
    assert chain[1:-1] == pytest.approx([(5, 0), (10, 0), (15, 0)])


def test_route_along_a_lane_uses_its_nodes():
    # Lane 10 → 11 → 12 from x = 10 to x = 30 at z = 0.
    lanes = [
        PlannedLane(10, 11, (10, 0), (20, 0)),
        PlannedLane(11, 12, (20, 0), (30, 0)),
    ]
    positions = {1: (0, 0), 2: (40, 0), 10: (10, 0), 11: (20, 0), 12: (30, 0)}

    chain = route_nodes(line((0, 0), (40, 0)), 1, 2, positions, lanes, 5.0)

    shared = [item for item in chain if isinstance(item, int)]
    assert shared == [1, 10, 11, 12, 2]


def test_crossing_lanes_are_not_shared():
    lanes = [PlannedLane(10, 11, (10, -10), (10, 10))]
    positions = {1: (0, 0), 2: (20, 0), 10: (10, -10), 11: (10, 10)}

    chain = route_nodes(line((0, 0), (20, 0)), 1, 2, positions, lanes, 5.0)

    assert [item for item in chain if isinstance(item, int)] == [1, 2]


def test_way_back_along_a_lane_runs_its_nodes_backwards():
    lanes = [PlannedLane(1, 3, (0, 0), (10, 0)), PlannedLane(3, 2, (10, 0), (20, 0))]
    positions = {1: (0, 0), 2: (20, 0), 3: (10, 0)}

    chain = route_nodes(line((20, 0), (0, 0)), 2, 1, positions, lanes, 5.0)

    assert chain == [2, 3, 1]


def test_pairs_against_a_one_way_connection_become_dual():
    data = data_with((1, 0, 0), (2, 10, 0), (3, 20, 0), connections=[(1, 2, REGULAR)])

    connections = chain_connections(data, [2, 1, 3])

    assert connections == [(2, 1, DUAL), (1, 3, REGULAR)]


def test_pairs_already_connected_in_the_driving_direction_are_kept():
    data = data_with((1, 0, 0), (2, 10, 0), (3, 20, 0), connections=[(1, 2, REGULAR), (2, 3, DUAL)])

    assert chain_connections(data, [1, 2, 3]) == []


def test_planned_lanes_are_the_connections_between_planned_nodes():
    data = data_with((1, 0, 0), (2, 10, 0), (3, 20, 0), connections=[(1, 2, DUAL), (2, 3, REGULAR)])

    lanes = planned_lanes(data, {1, 2})

    assert {(lane.source_id, lane.target_id) for lane in lanes} == {(1, 2), (2, 1)}


def test_node_headings_follow_the_connections():
    data = data_with((1, 0, 0), (2, 10, 0), (3, 10, 10), connections=[(1, 2, REGULAR)])
    write_connection_state(data, 2, 3, REGULAR)

    assert node_headings(data, 2) == pytest.approx((0.0, math.pi / 2))
    assert node_headings(data, 3) == pytest.approx((math.pi / 2,))
    assert node_headings(data_with((5, 0, 0)), 5) is None
