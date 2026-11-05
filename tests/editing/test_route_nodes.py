import math
from itertools import pairwise

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


def gaps(chain, positions):
    """The distances between the chain's nodes, each with the start of its connection."""

    points = [positions[item] if isinstance(item, int) else item for item in chain]

    return [(math.dist(a, b), a) for a, b in pairwise(points)]


def test_free_nodes_are_spaced_like_autodrive_records_a_drive_and_curves_by_turn():
    # 30 m east, then a quarter circle of 6 m radius to the north: a node each 15°, ~1.6 m.
    angles = [i / 40 * math.pi / 2 for i in range(1, 41)]
    arc = [(30 + 6 * math.sin(a), 6 - 6 * math.cos(a)) for a in angles]
    positions = {1: (0, 0), 2: arc[-1]}

    chain = route_nodes(line((0, 0), (30, 0)) + arc, 1, 2, positions, [], 20.0)

    straight = [gap for gap, start in gaps(chain, positions) if start[0] < 30]
    curve = [gap for gap, start in gaps(chain, positions) if start[0] > 30]
    assert max(straight) == pytest.approx(12)
    # The last gap is what is left before the end.
    assert curve and 1.2 <= min(curve[:-1]) and max(curve) <= 2.0 and curve[-1] >= 0.5


def test_the_last_free_node_is_not_squeezed_against_the_end():
    positions = {1: (0, 0), 2: (22, 0)}

    chain = route_nodes(line((0, 0), (22, 0)), 1, 2, positions, [], 5.0)

    assert all(2.5 <= gap <= 5 + 1e-9 for gap, _ in gaps(chain, positions))


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


def test_a_route_meeting_a_lane_only_near_its_end_does_not_turn_back_to_its_start():
    # Lane 10 → 2 from (0, 20) to the goal at (40, 0); the route comes in from (0, 0) and runs
    # along the lane's last 4 m only.
    lanes = [PlannedLane(10, 2, (0, 20), (40, 0))]
    positions = {1: (0, 0), 2: (40, 0), 10: (0, 20)}
    lane_x, lane_z = 40 / math.hypot(40, 20), -20 / math.hypot(40, 20)
    joint = (40 - 4 * lane_x, -4 * lane_z)
    points = line((0, 0), joint) + line(joint, (40, 0))[1:]

    chain = route_nodes(points, 1, 2, positions, lanes, 5.0)

    assert 10 not in chain


def test_the_stretch_into_the_goal_or_out_of_the_start_is_not_shared():
    # Lanes 1 → 4 and 5 → 2 lie under the route's first and last 5 m.
    lanes = [PlannedLane(1, 4, (0, 0), (5, 0)), PlannedLane(5, 2, (35, 0), (40, 0))]
    positions = {1: (0, 0), 2: (40, 0), 4: (5, 0), 5: (35, 0)}

    chain = route_nodes(line((0, 0), (40, 0)), 1, 2, positions, lanes, 5.0)

    assert [item for item in chain if isinstance(item, int)] == [1, 2]


def test_lanes_of_a_route_with_the_same_start_are_shared_from_the_start():
    # A route from the same start ran along 1 → 4 → 5 first.
    lanes = [PlannedLane(1, 4, (0, 0), (5, 0)), PlannedLane(4, 5, (5, 0), (10, 0))]
    positions = {1: (0, 0), 2: (40, 0), 4: (5, 0), 5: (10, 0)}

    chain = route_nodes(
        line((0, 0), (40, 0)), 1, 2, positions, lanes, 5.0, shared_ends=frozenset({(1, 4), (4, 5)})
    )

    assert [item for item in chain if isinstance(item, int)] == [1, 4, 5, 2]


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
