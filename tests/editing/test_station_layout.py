import pytest

from autodrive_editor.editing.station_layout import (
    StationSettings,
    StopChoice,
    building_stops_at,
    default_group,
    default_marker_name,
    lane_points,
    occupied,
    plan_stations,
    unique_name,
)
from autodrive_editor.file_io.savegame_stations import Stop, StopKind
from autodrive_editor.model.autodrive_data import NodeData


def stop(
    heading=90.0, position=(100.0, 5.0, 200.0), kind=StopKind.SELL, name="Grain store "
) -> Stop:
    return Stop("store.xml", "7", name, kind, ("WHEAT",), position, heading, True)


def test_lane_runs_along_the_arrow_with_a_node_at_the_stop():
    points, index = lane_points(stop(heading=90.0), StationSettings(10, 10, 5))

    assert points == pytest.approx(
        [(90, 5, 200), (95, 5, 200), (100, 5, 200), (105, 5, 200), (110, 5, 200)]
    )
    assert index == 2


def test_heading_zero_points_up_the_map():
    points, _ = lane_points(stop(heading=0.0), StationSettings(5, 5, 5))

    assert points == pytest.approx([(100, 5, 205), (100, 5, 200), (100, 5, 195)])


def test_turned_lane_runs_against_the_arrow():
    points, index = lane_points(stop(heading=90.0), StationSettings(10, 5, 5), turned=True)

    assert points[0] == pytest.approx((110, 5, 200))
    assert points[-1] == pytest.approx((95, 5, 200))
    assert points[index] == pytest.approx((100, 5, 200))


def test_stop_node_stays_at_the_stop_when_the_spacing_does_not_divide_the_lane():
    points, index = lane_points(stop(), StationSettings(7, 3, 5))

    assert points[index] == pytest.approx((100, 5, 200))
    assert points[0] == pytest.approx((93, 5, 200))
    assert points[-1] == pytest.approx((103, 5, 200))


def test_lane_without_length_before_or_after_starts_or_ends_at_the_stop():
    points, index = lane_points(stop(), StationSettings(0, 5, 5))
    assert index == 0 and points[0] == pytest.approx((100, 5, 200))

    points, index = lane_points(stop(), StationSettings(5, 0, 5))
    assert index == len(points) - 1 and points[-1] == pytest.approx((100, 5, 200))


def test_plan_has_one_way_lanes_markers_and_open_ends():
    choices = [
        StopChoice(stop(), "A", "Selling points"),
        StopChoice(stop(position=(0, 0, 0)), "B", "Productions", turned=True),
    ]
    network = plan_stations(choices, StationSettings(5, 5, 5))

    assert len(network.points) == 6
    assert network.connections == [(0, 1), (1, 2), (3, 4), (4, 5)]
    assert network.markers == [(1, "A", "Selling points"), (4, "B", "Productions")]
    assert network.open_ends == [0, 2, 3, 5]


def test_default_marker_name_and_group():
    assert default_marker_name(stop()) == "Grain store (Selling point)"
    assert default_group(StopKind.PRODUCTION) == "Productions"
    assert all(default_group(kind) for kind in StopKind)


def test_unique_name_adds_the_lowest_free_number():
    taken = {("A", "G"), ("A 2", "G"), ("B", "H")}

    assert unique_name("A", "G", taken) == "A 3"
    assert unique_name("A", "H", taken) == "A"


def test_occupied_finds_an_existing_node_on_the_lane():
    points, _ = lane_points(stop(), StationSettings(10, 10, 5))

    assert occupied(points, [NodeData(1, 104.5, 0, 200.5)])
    assert not occupied(points, [NodeData(1, 104.5, 0, 202), NodeData(2, 130, 0, 200)])


def test_building_stops_at_picks_the_building_of_the_closest_stop():
    a1 = stop(position=(0, 0, 0))
    a2 = stop(position=(30, 0, 0))
    b = Stop("b.xml", "8", "B", StopKind.LOAD, (), (40, 0, 0), 0.0, False)
    stops = [a1, a2, b]

    assert building_stops_at(stops, 37, 0, 5) == [b]
    assert building_stops_at(stops, 33, 0, 5) == [a1, a2]
    # Between the stops of a building, away from each of them.
    assert building_stops_at(stops, 15, 3, 5) == [a1, a2]
    assert building_stops_at(stops, 15, 10, 5) == []
