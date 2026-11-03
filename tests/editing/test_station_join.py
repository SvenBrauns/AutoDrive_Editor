from itertools import pairwise

import pytest
from costmap_helpers import make_costmap

from autodrive_editor.editing.junction import CurveKind
from autodrive_editor.editing.route_finder import Vehicle
from autodrive_editor.editing.station_join import direct_command, nearest_road, plan_direct
from autodrive_editor.editing.station_layout import StationSettings, StopChoice
from autodrive_editor.file_io.savegame_stations import Stop, StopKind
from autodrive_editor.model.autodrive_data import (
    REGULAR_FLAG,
    SUBPRIO_FLAG,
    AutoDriveData,
    MarkerData,
    NodeData,
)
from autodrive_editor.model.connections import (
    CONNECTION_STATES,
    ConnectionType,
    write_connection_state,
)

VEHICLE = Vehicle(width=3, margin=0.5)
SETTINGS = StationSettings(10, 10, 12, 8, 50)


def road(data, first_id, points, connection_type=ConnectionType.REGULAR):
    ids = list(range(first_id, first_id + len(points)))

    for node_id, (x, z) in zip(ids, points, strict=True):
        data.add_node(NodeData(node_id, x, 0, z))

    for source, target in pairwise(ids):
        write_connection_state(data, source, target, CONNECTION_STATES[connection_type])

    return ids


def east_road(connection_type=ConnectionType.REGULAR):
    """A road at z = 0 from x = -100 to 100 heading east, IDs 1–21."""

    data = AutoDriveData()
    road(data, 1, [(x, 0.0) for x in range(-100, 101, 10)], connection_type)

    return data


def choice(z=30.0, heading=90.0) -> StopChoice:
    """A stop south of the road (z grows southwards), its lane heading east by default."""

    stop = Stop("store.xml", "7", "Store", StopKind.SELL, ("WHEAT",), (0, 0, z), heading, True)

    return StopChoice(stop, "Store", "Selling points", heading)


def applied(data, choices, joins):
    command, open_ends = direct_command(data, choices, joins, SETTINGS, lambda *_: 0.0)
    command.apply()

    return command, open_ends


def reachable(data, start_id):
    seen, todo = {start_id}, [start_id]

    while todo:
        for target_id in data.nodes[todo.pop()].outgoing - seen:
            seen.add(target_id)
            todo.append(target_id)

    return seen


def test_a_stop_beside_a_one_way_road_gets_a_way_in_and_out():
    data = east_road()

    join = plan_direct(data, choice(), SETTINGS, 6.0, None, VEHICLE)

    assert [curve.kind for curve in join.curves] == [CurveKind.IN, CurveKind.OUT]
    assert join.missing == []

    _, open_ends = applied(data, [choice()], [join])
    (marker_id,) = data.markers

    assert open_ends == []
    assert marker_id in reachable(data, 1)
    assert 21 in reachable(data, marker_id)
    assert data.validate_connections() == []


def test_leg_nodes_are_subprio_and_road_splits_keep_the_road_type():
    data = east_road()
    road_ids = set(data.nodes)
    join = plan_direct(data, choice(), SETTINGS, 6.0, None, VEHICLE)

    command, _ = applied(data, [choice()], [join])

    on_road = {node.node_id for node in command.new_nodes if node.z == pytest.approx(0)}

    assert on_road, "the legs split the road"
    assert all(data.nodes[node_id].flag == REGULAR_FLAG for node_id in on_road)
    assert all(
        node.flag == SUBPRIO_FLAG for node in command.new_nodes if node.node_id not in on_road
    )
    # The road still runs through from end to end.
    assert 21 in reachable(data, 1)
    assert road_ids < set(data.nodes)


def test_a_stop_by_a_two_way_road_is_reached_from_both_directions():
    data = east_road(ConnectionType.DUAL)

    join = plan_direct(data, choice(), SETTINGS, 6.0, None, VEHICLE)

    kinds = sorted(curve.kind.value for curve in join.curves)
    assert kinds == ["in", "in", "out", "out"]


def test_a_stop_beyond_the_reach_keeps_its_lane_with_both_ends_open():
    data = east_road()

    join = plan_direct(data, choice(z=80.0), SETTINGS, 6.0, None, VEHICLE)

    assert join.curves == []
    assert len(join.missing) == 1

    command, open_ends = applied(data, [choice(z=80.0)], [join])

    assert len(open_ends) == 2
    assert len(data.markers) == 1
    assert len(command.new_nodes) == 4


def test_a_blocked_leg_is_listed_with_a_gap():
    # A wall between the road and the start of the lane, from x = -60 to 0.
    costmap = make_costmap(300, blocked=[(-60, 10, 0, 20)])

    join = plan_direct(east_road(), choice(), SETTINGS, 6.0, costmap, VEHICLE)

    assert not join.has_way_in
    assert join.has_way_out
    assert len(join.missing) == len(join.gaps) == 1


def test_subprio_and_marker_connections_are_no_road():
    data = east_road()
    road(data, 50, [(-20.0, 20.0), (20.0, 20.0)])
    data.nodes[50].flag = data.nodes[51].flag = SUBPRIO_FLAG
    road(data, 60, [(-20.0, 25.0), (20.0, 25.0)])
    data.add_marker(MarkerData(60, "Silo", "All"))

    assert nearest_road(data, (5.0, 30.0), 50.0) == (11, 12)
    assert nearest_road(data, (5.0, 30.0), 20.0) is None
