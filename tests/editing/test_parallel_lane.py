import math

import pytest

from autodrive_editor.editing.parallel_lane import (
    ParallelLaneError,
    TightCurveError,
    offset_polyline,
    parallel_lane,
    selected_chains,
    signed_distance,
)
from autodrive_editor.model.autodrive_data import AutoDriveData, NodeData
from autodrive_editor.model.connections import CONNECTION_STATES, ConnectionType
from autodrive_editor.model.connections import write_connection_state as connect


def road(points, connection_type=ConnectionType.REGULAR, first_id=1, data=None):
    """Nodes at the (x, y, z) points, connected one after another."""

    data = data or AutoDriveData()
    ids = range(first_id, first_id + len(points))

    for node_id, (x, y, z) in zip(ids, points, strict=True):
        data.add_node(NodeData(node_id, x, y, z))

    for source, target in zip(ids, ids[1:], strict=False):
        connect(data, source, target, CONNECTION_STATES[connection_type])

    return data


def straight(length=20, step=5, data=None, first_id=1, **kwargs):
    points = [(x, 0, 0) for x in range(0, length + 1, step)]
    return road(points, data=data, first_id=first_id, **kwargs)


# --- chains ---------------------------------------------------------------


def test_chain_is_ordered_in_driving_direction():
    data = road([(x, 0, 0) for x in (20, 15, 10, 5, 0)])  # 1 -> 5 drives towards x = 0

    (chain,) = selected_chains(data, [5, 3, 1, 2, 4])

    assert chain.node_ids == (1, 2, 3, 4, 5)
    assert chain.state == CONNECTION_STATES[ConnectionType.REGULAR]


def test_reverse_chain_keeps_its_direction():
    data = road([(x, 0, 0) for x in (0, 5, 10)], ConnectionType.REVERSE)

    (chain,) = selected_chains(data, [3, 2, 1])

    assert chain.node_ids == (1, 2, 3)
    assert chain.state == CONNECTION_STATES[ConnectionType.REVERSE]


def test_several_chains_and_lone_nodes():
    data = straight()
    straight(data=data, first_id=10)
    data.add_node(NodeData(99, 50, 0, 50))

    chains = selected_chains(data, [1, 2, 3, 10, 11, 99])

    assert [chain.node_ids for chain in chains] == [(1, 2, 3), (10, 11)]


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda data: connect(data, 1, 5, CONNECTION_STATES[ConnectionType.REGULAR]), "ring"),
        (lambda data: connect(data, 2, 4, CONNECTION_STATES[ConnectionType.REGULAR]), "junction"),
        (lambda data: connect(data, 2, 3, CONNECTION_STATES[ConnectionType.DUAL]), "differ"),
    ],
)
def test_chain_is_refused(change, message):
    data = straight()
    change(data)

    with pytest.raises(ParallelLaneError, match=message):
        selected_chains(data, [1, 2, 3, 4, 5])


# --- offset ---------------------------------------------------------------


def test_positive_offset_lies_right_of_the_direction():
    # Driving east (+x), right is +z on the map.
    assert offset_polyline([(0, 0), (10, 0)], 2) == [(0, 2), (10, 2)]
    assert offset_polyline([(0, 0), (10, 0)], -2) == [(0, -2), (10, -2)]


def test_corner_keeps_the_distance_to_both_legs():
    offset = offset_polyline([(0, 0), (10, 0), (10, 10)], -2)  # left turn, outer side

    assert offset[1] == pytest.approx((12, -2))


def test_curve_tighter_than_the_distance_is_refused():
    # Square corner with 2 m legs: the inner offset of 3 m would run backwards.
    with pytest.raises(TightCurveError):
        offset_polyline([(0, 0), (2, 0), (2, 2), (0, 2)], 3)

    offset_polyline([(0, 0), (2, 0), (2, 2), (0, 2)], -3)  # outer side is fine


def test_signed_distance_of_the_pointer():
    points = [(0, 0), (10, 0), (20, 0)]

    assert signed_distance(points, 5, 3) == pytest.approx(3)
    assert signed_distance(points, 15, -4) == pytest.approx(-4)


# --- lane nodes -----------------------------------------------------------


def test_lane_is_respaced_and_follows_the_height():
    data = road([(0, 0, 0), (7, 7, 0), (20, 20, 0)])
    (chain,) = selected_chains(data, [1, 2, 3])

    lane = parallel_lane(data, chain, distance=5.5, spacing=5, opposite=False)

    assert len(lane) == 5
    assert [z for _, _, z in lane] == pytest.approx([5.5] * 5)
    assert [x for x, _, _ in lane] == pytest.approx([0, 5, 10, 15, 20])
    assert [y for _, y, _ in lane] == pytest.approx([0, 5, 10, 15, 20])


def test_opposite_lane_runs_the_other_way():
    data = straight()
    (chain,) = selected_chains(data, [1, 2, 3, 4, 5])

    lane = parallel_lane(data, chain, distance=-4, spacing=5, opposite=True)

    assert lane[0][0] == pytest.approx(20)
    assert lane[-1][0] == pytest.approx(0)


def test_lane_beside_an_arc_keeps_the_distance():
    radius = 30
    points = [
        (radius * math.cos(a / 10), 0, radius * math.sin(a / 10)) for a in range(0, 16)
    ]  # turns right (towards +z, then -x), centre at the origin
    data = road(points)
    (chain,) = selected_chains(data, range(1, 17))

    for distance in (5.5, -5.5):
        lane = parallel_lane(data, chain, distance=distance, spacing=3, opposite=False)
        radii = [math.hypot(x, z) for x, _, z in lane]

        assert radii == pytest.approx([radius - distance] * len(lane), abs=0.15)


def test_tight_curve_names_the_node():
    data = road([(0, 0, 0), (2, 0, 0), (2, 0, 2), (0, 0, 2)])
    (chain,) = selected_chains(data, [1, 2, 3, 4])

    with pytest.raises(ParallelLaneError, match="node [23]"):
        parallel_lane(data, chain, distance=3, spacing=5, opposite=False)
