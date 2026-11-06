import math

import pytest
from costmap_helpers import make_costmap

from autodrive_editor.editing.stations.fill_type_names import fill_type_name
from autodrive_editor.editing.stations.station_layout import (
    LaneEnd,
    MarkerRule,
    StationSettings,
    StopChoice,
    building_stops_at,
    can_join,
    default_group,
    default_heading,
    default_marker_rules,
    free_reach,
    lane_points,
    marker_names,
    occupied,
    pattern_problem,
    plan_stations,
    stations_command,
    unique_name,
)
from autodrive_editor.file_io.savegame_stations import Stop, StopKind
from autodrive_editor.model.autodrive_data import SUBPRIO_FLAG, AutoDriveData, NodeData
from autodrive_editor.model.connections import ConnectionType


def stop(
    heading=90.0,
    position=(100.0, 5.0, 200.0),
    kind=StopKind.SELL,
    name="Grain store ",
    ai_node=True,
    building=(0.0, 0.0),
    fill_types=("WHEAT",),
    loads=False,
) -> Stop:
    return Stop(
        "store.xml", "7", name, kind, fill_types, position, heading, ai_node, building, loads
    )


def test_lane_runs_along_the_arrow_with_a_node_at_the_stop():
    points, index = lane_points(stop(), StationSettings(10, 10, 5, 0), 90)

    assert points == pytest.approx(
        [(90, 5, 200), (95, 5, 200), (100, 5, 200), (105, 5, 200), (110, 5, 200)]
    )
    assert index == 2


def test_heading_zero_points_up_the_map():
    points, _ = lane_points(stop(), StationSettings(5, 5, 5, 0), 0)

    assert points == pytest.approx([(100, 5, 205), (100, 5, 200), (100, 5, 195)])


def test_lane_heading_west_starts_east_of_the_stop():
    points, index = lane_points(stop(), StationSettings(10, 5, 5, 0), 270)

    assert points[0] == pytest.approx((110, 5, 200))
    assert points[-1] == pytest.approx((95, 5, 200))
    assert points[index] == pytest.approx((100, 5, 200))


def test_stop_node_stays_at_the_stop_when_the_spacing_does_not_divide_the_lane():
    points, index = lane_points(stop(), StationSettings(7, 3, 5, 0), 90)

    assert points[index] == pytest.approx((100, 5, 200))
    assert points[0] == pytest.approx((93, 5, 200))
    assert points[-1] == pytest.approx((103, 5, 200))


def test_lane_without_length_before_or_after_starts_or_ends_at_the_stop():
    points, index = lane_points(stop(), StationSettings(0, 5, 5, 0), 90)
    assert index == 0 and points[0] == pytest.approx((100, 5, 200))

    points, index = lane_points(stop(), StationSettings(5, 0, 5, 0), 90)
    assert index == len(points) - 1 and points[-1] == pytest.approx((100, 5, 200))


def test_marker_lies_the_offset_past_the_stop_and_the_lane_goes_on_after_it():
    points, index = lane_points(stop(), StationSettings(5, 5, 5, 8), 90)

    assert points[index] == pytest.approx((108, 5, 200))
    assert points[0] == pytest.approx((95, 5, 200))
    assert points[-1] == pytest.approx((113, 5, 200))


def test_marker_without_lane_before_still_starts_at_the_stop():
    points, index = lane_points(stop(), StationSettings(0, 0, 5, 8), 90)

    assert points[0] == pytest.approx((100, 5, 200))
    assert index == len(points) - 1 and points[-1] == pytest.approx((108, 5, 200))


def test_a_dragged_end_bends_its_leg_in_one_arc_from_the_stop():
    # Heading right from (100, 200) to (110, 210): a quarter circle around (100, 210).
    settings = StationSettings(5, 5, 5, 5)
    points, index = lane_points(stop(), settings, 90, end=LaneEnd(110, 210))

    assert points[0] == pytest.approx((95, 5, 200))
    assert points[-1] == pytest.approx((110, 5, 210))
    assert all(
        math.dist((x, z), (100, 210)) == pytest.approx(10, abs=0.01) for x, _, z in points[index:]
    )
    # The marker 5 m along the arc.
    assert points[index] == pytest.approx(
        (100 + 10 * math.sin(0.5), 5, 210 - 10 * math.cos(0.5)), abs=0.01
    )


def test_a_dragged_start_bends_the_leg_behind_the_stop():
    points, index = lane_points(stop(), StationSettings(5, 5, 5, 5), 90, start=LaneEnd(90, 190))

    assert points[0] == pytest.approx((90, 5, 190))
    assert all(
        math.dist((x, z), (100, 190)) == pytest.approx(10, abs=0.01) for x, _, z in points[:3]
    )
    assert points[index] == pytest.approx((105, 5, 200))


def test_a_lane_end_dropped_on_a_node_joins_it():
    data = AutoDriveData()
    data.add_node(NodeData(1, 120, 0, 210))
    joined = StopChoice(stop(), "A", "G", 90, end=LaneEnd(120, 210, 1))

    command = stations_command(data, [joined], StationSettings(5, 5, 5, 0))
    command.apply()

    (marker_id,) = data.markers
    assert 1 not in {node.node_id for node in command.new_nodes}
    assert data.nodes[1].incoming and all(n.is_subprio for n in command.new_nodes)
    assert marker_id != 1


def test_a_lane_starts_at_a_node_driven_to_and_ends_at_one_driven_from():
    data = AutoDriveData()
    data.add_node(NodeData(1, 0, 0, 0, outgoing={2}))
    data.add_node(NodeData(2, 10, 0, 0, incoming={1}))

    assert can_join(data, 2, at_start=True) and can_join(data, 1, at_start=False)
    assert not can_join(data, 1, at_start=True) and not can_join(data, 2, at_start=False)


def test_plan_has_one_way_lanes_markers_and_open_ends():
    choices = [
        StopChoice(stop(), "A", "Selling points", 90),
        StopChoice(stop(position=(0, 0, 0)), "B", "Productions", 270),
    ]
    network = plan_stations(choices, StationSettings(5, 5, 5, 0))

    assert len(network.points) == 6
    assert network.connections == [
        (s, t, ConnectionType.REGULAR) for s, t in [(0, 1), (1, 2), (3, 4), (4, 5)]
    ]
    assert network.flags == [SUBPRIO_FLAG] * 6
    assert network.markers == [(1, "A", "Selling points"), (4, "B", "Productions")]
    assert network.open_ends == [0, 2, 3, 5]


def test_default_marker_name_and_group():
    assert marker_names([stop()], default_marker_rules(), set()) == [
        ("Grain store (Selling point)", "Selling points")
    ]
    assert default_group(StopKind.PRODUCTION) == "Productions"
    assert all(default_group(kind) for kind in StopKind)


def test_productions_are_named_by_fill_type_and_action_in_a_group_per_building():
    production = StopKind.PRODUCTION
    stops = [
        stop(kind=production, name="Distillery", fill_types=("DIESEL",)),
        stop(kind=production, name="Distillery", fill_types=("WHISKEY", "RUM"), loads=True),
        stop(kind=production, name="Distillery", fill_types=("SUGARBEET_CUT",)),
        stop(kind=production, name="Distillery", fill_types=()),
    ]

    assert marker_names(stops, default_marker_rules(), set()) == [
        ("Diesel-unload", "prod.Distillery"),
        ("Whiskey-load", "prod.Distillery"),
        ("Sugarbeet cut-unload", "prod.Distillery"),
        ("Distillery-unload", "prod.Distillery"),
    ]


def test_fill_type_names_are_translated_or_made_readable(german):
    assert fill_type_name("WATER") == "Wasser"
    assert fill_type_name("farmSilo") == "Farm silo"


def test_marker_names_follow_the_rule_of_the_stop_type():
    rules = default_marker_rules() | {StopKind.PRODUCTION: MarkerRule("VK-{building}", "VK")}
    stops = [stop(kind=StopKind.PRODUCTION), stop(), stop(kind=StopKind.PRODUCTION)]

    assert marker_names(stops, rules, {("VK-Grain store", "VK")}) == [
        ("VK-Grain store 2", "VK"),
        ("Grain store (Selling point)", "Selling points"),
        ("VK-Grain store 3", "VK"),
    ]


def test_numbers_count_per_group_and_skip_taken_names():
    rules = {kind: MarkerRule("{n:03}-{type}", "G") for kind in StopKind}
    stops = [stop(), stop(kind=StopKind.LOAD), stop()]

    assert marker_names(stops, rules, {("006-Loading", "G")}, start=5) == [
        ("005-Selling point", "G"),
        ("007-Loading", "G"),
        ("008-Selling point", "G"),
    ]


def test_pattern_problem():
    assert pattern_problem("{n:03}-{building} ({type})") is None
    assert pattern_problem("{fill}-{action}") is None
    assert pattern_problem("prod.{building}", group=True) is None
    assert pattern_problem("G-{n}", group=True) is not None
    assert "{name}" in pattern_problem("VK-{name}")
    assert pattern_problem("VK-{building") is not None
    assert pattern_problem("{n:x.}") is not None
    assert pattern_problem("  ") is not None


def test_unique_name_adds_the_lowest_free_number():
    taken = {("A", "G"), ("A 2", "G"), ("B", "H")}

    assert unique_name("A", "G", taken) == "A 3"
    assert unique_name("A", "H", taken) == "A"


def test_occupied_finds_an_existing_node_on_the_lane():
    points, _ = lane_points(stop(), StationSettings(10, 10, 5, 0), 90)

    assert occupied(points, [NodeData(1, 104.5, 0, 200.5)])
    assert not occupied(points, [NodeData(1, 104.5, 0, 202), NodeData(2, 130, 0, 200)])


def test_building_stops_at_picks_every_building_with_a_stop_near_the_click():
    a1 = stop(position=(0, 0, 0))
    a2 = stop(position=(60, 0, 0))
    b = Stop("b.xml", "8", "B", StopKind.LOAD, (), (75, 0, 0), 0.0, False)
    stops = [a1, a2, b]

    assert building_stops_at(stops, 88, 0, 5) == [b]
    # Between two buildings, within 15 m of both.
    assert building_stops_at(stops, 67, 0, 5) == stops
    # Between the stops of a building, away from each of them.
    assert building_stops_at(stops, 30, 3, 5) == [a1, a2]
    assert building_stops_at(stops, 30, 20, 5) == []


def test_free_reach_ends_at_the_first_blocked_cell_beside_or_on_the_lane():
    costmap = make_costmap(blocked=[(10, 1, 12, 3)])

    # Blocked 10 m to the right, 1.5 m beside the lane counts too.
    assert free_reach(costmap, 0, 0, 90) == 10
    assert free_reach(costmap, 0, 0, 270) == 40
    # Cells right next to the stop are skipped (lanes under a roof).
    assert free_reach(make_costmap(blocked=[(-1, -1, 2, 2)]), 0, 0, 0) == 40


def test_default_heading_takes_the_freest_axis():
    # A corridor running up and down, walls left and right of the stop.
    costmap = make_costmap(blocked=[(-60, -60, -4, 60), (4, -60, 60, 60)])
    turned = stop(heading=90, position=(0, 0, 0), ai_node=False, building=(0, 0))

    assert default_heading(turned, costmap) in (0, 180)


def test_ai_node_axis_or_the_one_across_it():
    costmap = make_costmap(blocked=[(-60, -60, -4, 60), (4, -60, 60, 60)])

    # 45° is neither the axis nor across it from 0°, so 0° or 180° is taken.
    assert default_heading(stop(heading=0, position=(0, 0, 0)), costmap) in (0, 180)
    # Across the AI node's axis.
    assert default_heading(stop(heading=90, position=(0, 0, 0)), costmap) in (0, 180)


def test_stops_circle_their_building_counterclockwise():
    building = (0.0, 0.0)
    east = stop(heading=0, position=(20, 0, 0), building=building)
    west = stop(heading=0, position=(-20, 0, 0), building=building)

    # Up the map on the east side, down on the west side (z points down).
    assert default_heading(east, make_costmap()) == 0
    assert default_heading(west, make_costmap()) == 180
    assert default_heading(west, None) == 180


def test_lane_towards_the_building_heads_to_the_freer_side():
    # The stop is south of the building in a north–south corridor that ends at the building.
    costmap = make_costmap(blocked=[(-10, -30, 10, 5), (-60, 6, -4, 60), (4, 6, 60, 60)])
    south = stop(heading=0, position=(0, 0, 20), building=(0, 0))

    assert default_heading(south, costmap) == 180
