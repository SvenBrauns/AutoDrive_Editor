from itertools import pairwise

from costmap_helpers import BLOCKED, GRASS, ROAD, make_costmap

from autodrive_editor.editing.junction import CurveKind
from autodrive_editor.editing.route_finder import RouteFinder, Vehicle
from autodrive_editor.editing.station_join import (
    direct_command,
    nearest_road,
    plan_direct,
    preview_piece,
)
from autodrive_editor.editing.station_layout import StationSettings, StopChoice
from autodrive_editor.file_io.navigation_costmap import NavigationCostmap
from autodrive_editor.file_io.savegame_stations import Stop, StopKind
from autodrive_editor.model.autodrive_data import (
    MAP_SCAN_FLAG,
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
SIZE = 300
ALL_ROAD = make_costmap(SIZE)


def road(data, first_id, points, connection_type=ConnectionType.REGULAR, flag=MAP_SCAN_FLAG):
    ids = list(range(first_id, first_id + len(points)))

    for node_id, (x, z) in zip(ids, points, strict=True):
        data.add_node(NodeData(node_id, x, 0, z, flag))

    for source, target in pairwise(ids):
        write_connection_state(data, source, target, CONNECTION_STATES[connection_type])

    return ids


def east_road(connection_type=ConnectionType.DUAL, flag=MAP_SCAN_FLAG):
    """A road of the map scan at z = 0 from x = -100 to 100, IDs 1–21; two-way by default."""

    data = AutoDriveData()
    road(data, 1, [(x, 0.0) for x in range(-100, 101, 10)], connection_type, flag)

    return data


def choice(z=30.0, heading=90.0) -> StopChoice:
    """A stop south of the road (z grows southwards), its lane heading east by default."""

    stop = Stop("store.xml", "7", "Store", StopKind.SELL, ("WHEAT",), (0, 0, z), heading, True)

    return StopChoice(stop, "Store", "Selling points", heading)


def costmap(value, areas) -> NavigationCostmap:
    """A map of one value with (x1, z1, x2, z2, value) rectangles on it."""

    cells = bytearray([value]) * (SIZE * SIZE)

    for x1, z1, x2, z2, area_value in areas:
        for z in range(z1, z2):
            for x in range(x1, x2):
                cells[(z + SIZE // 2) * SIZE + x + SIZE // 2] = area_value

    return NavigationCostmap(SIZE, SIZE, bytes(cells))


def plan(data, stop=None, cost=ALL_ROAD, find_route=None):
    return plan_direct(data, stop or choice(), SETTINGS, 6.0, cost, VEHICLE, find_route)


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


def test_a_stop_by_a_public_road_is_reached_from_and_left_to_both_directions():
    data = east_road()

    join = plan(data)

    assert join.has_way_in and join.has_way_out
    kinds = sorted(curve.kind.value for d in join.driveways for curve in d.curves)
    assert kinds == ["in", "in", "out", "out"]

    _, open_ends = applied(data, [choice()], [join])
    (marker_id,) = data.markers

    assert open_ends == []
    assert marker_id in reachable(data, 1) and marker_id in reachable(data, 21)
    assert {1, 21} <= reachable(data, marker_id)
    assert data.validate_connections() == []


def test_lane_nodes_are_subprio_yard_nodes_regular_and_road_splits_keep_their_type():
    data = east_road()
    join = plan(data)

    command, _ = applied(data, [choice()], [join])

    lane = {node.node_id for node in command.new_nodes if node.z == 30}
    on_road = {node.node_id for node in command.new_nodes if node.z == 0}
    assert on_road, "the curves split the road"
    for node in command.new_nodes:
        if node.node_id in lane:
            assert node.flag == SUBPRIO_FLAG
        elif node.node_id in on_road:
            assert node.flag == MAP_SCAN_FLAG
        else:
            assert node.flag == REGULAR_FLAG


def test_a_road_built_by_hand_is_joined_with_one_curve_from_and_to_its_lane():
    data = east_road(flag=REGULAR_FLAG)

    join = plan(data)

    assert sorted(curve.kind.value for d in join.driveways for curve in d.curves) == ["in", "out"]


def test_the_ways_follow_the_yard_to_its_driveway():
    # Grass between road and yard; the yard (z 20–40) meets the road only at x 30–40.
    cost = costmap(
        GRASS, [(-150, -3, 150, 3, ROAD), (-50, 20, 50, 40, ROAD), (30, 0, 40, 20, ROAD)]
    )

    join = plan(east_road(), cost=cost)

    assert join.has_way_in and join.has_way_out
    for leg in join.legs:
        crossing = [x for x, z in leg.points if 5 < z < 15]
        assert crossing and all(28 <= x <= 42 for x in crossing)


def test_a_lane_under_a_roof_still_finds_its_ways():
    # A roof over the lane and 15 m beyond both its ends.
    cost = costmap(ROAD, [(-35, 25, 45, 36, BLOCKED)])

    join = plan(east_road(), cost=cost)

    assert join.has_way_in and join.has_way_out


def test_a_stop_beyond_the_reach_keeps_its_lane_with_both_ends_open():
    data = east_road()

    join = plan(data, choice(z=90.0))

    assert join.driveways == [] and len(join.missing) == 2

    command, open_ends = applied(data, [choice(z=90.0)], [join])

    assert len(open_ends) == 2
    assert len(data.markers) == 1
    assert len(command.new_nodes) == 4


def test_the_route_finder_builds_the_yard_legs():
    finder = RouteFinder(ALL_ROAD, VEHICLE)

    join = plan(east_road(), find_route=finder.find)

    assert join.has_way_in and join.has_way_out
    assert all(len(leg.points) > 2 for leg in join.legs)


def test_the_preview_joins_the_ways_to_the_lane_ends():
    join = plan(east_road())

    piece = preview_piece([choice()], [join], SETTINGS)

    start, end = piece.open_ends
    assert start in {target for _, target, _ in piece.connections}
    assert end in {source for source, _, _ in piece.connections}
    assert {leg.kind for leg in join.legs} == {CurveKind.IN, CurveKind.OUT}


def test_subprio_and_marker_connections_are_no_road():
    data = east_road(ConnectionType.REGULAR)
    road(data, 50, [(-20.0, 20.0), (20.0, 20.0)], flag=SUBPRIO_FLAG)
    road(data, 60, [(-20.0, 25.0), (20.0, 25.0)])
    data.add_marker(MarkerData(60, "Silo", "All"))

    assert nearest_road(data, (5.0, 30.0), 50.0) == (11, 12)
    assert nearest_road(data, (5.0, 30.0), 20.0) is None
