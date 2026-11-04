import pytest
from costmap_helpers import make_costmap

from autodrive_editor.editing.bunker_silo import silo_access, silo_settings
from autodrive_editor.editing.parking_layout import (
    ParkingMode,
    ShedFrame,
    bay_centers,
    from_template,
    plan_parking,
    template_values,
)
from autodrive_editor.file_io.savegame_sheds import IndoorArea
from autodrive_editor.model.connections import ConnectionType

# 10 m wide from x = -5 to 5, driven along z from 0 (back) to 20 (front).
SILO = IndoorArea("silo.xml", "s", ((-5, 0), (5, 0), (5, 20), (-5, 20)), height=0)
SIDE_WALLS = [(-6, -2, -5, 22), (5, -2, 6, 22)]
BACK_WALL = (-6, -2, 6, 0)
FRONT_WALL = (-6, 20, 6, 22)


@pytest.mark.parametrize(
    ("walls", "access"),
    [
        ([BACK_WALL], (ParkingMode.BACK_IN, "front")),
        ([FRONT_WALL], (ParkingMode.BACK_IN, "back")),
        ([], (ParkingMode.DRIVE_THROUGH, "front")),
    ],
)
def test_closed_end_is_found_from_the_drivability_map(walls, access):
    assert silo_access(SILO, make_costmap(60, blocked=SIDE_WALLS + walls)) == access


def test_turned_silo_is_entered_at_its_open_end():
    # The same silo turned by 90°: its back lies at x = 0, its front at x = -20.
    turned = IndoorArea("silo.xml", "s", ((0, -5), (0, 5), (-20, 5), (-20, -5)), height=0)

    front_wall = (-22, -6, -20, 6)

    assert silo_access(turned, make_costmap(60, blocked=[front_wall])) == (
        ParkingMode.BACK_IN,
        "back",
    )


def test_without_map_a_silo_is_backed_into_from_the_front():
    assert silo_access(SILO, None) == (ParkingMode.BACK_IN, "front")


@pytest.mark.parametrize(("width", "lanes"), [(26.6, 5), (33.0, 6), (11.5, 2), (3.0, 1)])
def test_one_lane_per_five_and_a_half_metres_of_width(width, lanes):
    area = IndoorArea("silo.xml", "s", ((0, 0), (width, 0), (width, 20), (0, 20)), height=0)
    layout = silo_settings(area, None)

    assert layout.bays == lanes
    frame = ShedFrame.from_area(area, layout.open_side)
    assert bay_centers(frame, layout) == pytest.approx(
        [width / lanes * (index + 0.5) for index in range(lanes)]
    )


def connections_of(network, connection_type):
    return {(s, t) for s, t, kind in network.connections if kind == connection_type}


def depths(network, nodes):
    return [network.points[node][1] for node in nodes]


def test_back_in_silo_layout():
    layout = silo_settings(SILO, make_costmap(60, blocked=SIDE_WALLS + [BACK_WALL]))
    network = plan_parking(ShedFrame.from_area(SILO, "front"), layout)

    # The front is open, so d runs from 0 there to 20 at the back wall.
    assert depths(network, [marker for marker, _, _ in network.markers]) == [17, 17]
    entry_ends, exit_ends = network.open_ends[:2], network.open_ends[2:]
    assert depths(network, entry_ends) == pytest.approx([-5.5] * 2, abs=1.5)
    assert depths(network, exit_ends) == pytest.approx([-22] * 2, abs=1.5)

    dual = {node for pair in connections_of(network, ConnectionType.DUAL) for node in pair}
    lane = sorted(set(depths(network, dual)), reverse=True)
    assert lane[:4] == [17, 16, 13, 10]
    assert lane[-1] <= -31


def test_drive_through_silo_lanes_end_at_their_markers():
    layout = silo_settings(SILO, make_costmap(60, blocked=SIDE_WALLS))
    network = plan_parking(ShedFrame.from_area(SILO, "front"), layout)
    markers = [marker for marker, _, _ in network.markers]

    assert depths(network, markers) == [35, 35]
    assert not any(source in markers for source, _, _ in network.connections)
    # Only the entry line, 20 m before the silo, has open ends.
    assert depths(network, network.open_ends) == [-20, -20]
    lane = sorted(d for (a, d) in network.points if a == network.points[markers[0]][0])
    assert lane[0] == -20 and max(b - a for a, b in zip(lane, lane[1:], strict=False)) <= 5


def test_a_silo_template_stays_a_silo():
    layout = silo_settings(SILO, None)

    assert from_template(template_values(layout)) == layout
