import math
from dataclasses import replace

import pytest

from autodrive_editor.editing.parking_layout import (
    OUTSIDE_NODES,
    TURN_STEPS,
    BayLine,
    ParkingMode,
    ParkingSettings,
    ShedFrame,
    bay_centers,
    bay_width,
    default_bay_line,
    default_open_side,
    drive_through_line,
    from_template,
    plan_parking,
    side_angle,
    template_values,
)
from autodrive_editor.file_io.savegame_sheds import IndoorArea
from autodrive_editor.model.connections import ConnectionType

# 30 × 15 m like easyShed01; the front (height end, +z) is at the bottom of the screen.
SHED = IndoorArea("shed.xml", "1", ((-15, -7.5), (15, -7.5), (15, 7.5), (-15, 7.5)), 90.0)


def settings(**values) -> ParkingSettings:
    defaults = dict(bays=4, gaps=(0.0, 0.0, 0.0), marker_name="Shed", start_number=3, group="G")

    return ParkingSettings(**(defaults | values))


def connections_of(network, connection_type):
    return {(s, t) for s, t, kind in network.connections if kind == connection_type}


def test_frame_of_the_front_starts_on_the_left_seen_from_outside():
    frame = ShedFrame.from_area(SHED, "front")

    assert frame.origin == (-15, 7.5)
    assert frame.along == (1, 0)
    assert frame.inward == (0, -1)
    assert (frame.length, frame.depth) == (30, 15)
    assert frame.to_map(30, 15) == (15, -7.5)


def test_frame_of_the_back_looks_the_other_way():
    frame = ShedFrame.from_area(SHED, "back")

    assert frame.origin == (15, -7.5)
    assert frame.along == (-1, 0)
    assert frame.inward == (0, 1)


def test_frame_of_a_short_side():
    frame = ShedFrame.from_area(SHED, "left")

    assert (frame.length, frame.depth) == (15, 30)
    assert frame.origin == (-15, -7.5)
    assert frame.inward == (1, 0)


def test_side_angles_point_outward():
    assert side_angle(SHED, "front") == pytest.approx(180)
    assert side_angle(SHED, "back") == pytest.approx(0)
    assert side_angle(SHED, "left") == pytest.approx(270)
    assert side_angle(SHED, "right") == pytest.approx(90)


def test_default_open_side_is_a_long_side():
    assert default_open_side(SHED) == "front"

    tall = IndoorArea("x", "2", ((0, 0), (10, 0), (10, 30), (0, 30)), 0.0)

    assert default_open_side(tall) == "left"


def test_bay_width_and_centers():
    frame = ShedFrame.from_area(SHED, "front")
    values = settings(left_offset=1.0, right_offset=1.0, gaps=(0.5, 0.5, 1.0))

    assert bay_width(frame, values) == pytest.approx(6.5)
    assert bay_centers(frame, values) == pytest.approx([4.25, 11.25, 18.25, 25.75])


def test_back_in_bay_line():
    frame = ShedFrame.from_area(SHED, "front")
    network = plan_parking(frame, settings(bays=1, gaps=(), back_offset=1.0))

    marker = network.markers[0][0]
    assert network.markers == [(marker, "Shed 3")]
    assert network.points[marker] == (15.0, 14.0)

    # The dual line runs from the marker straight out of the shed.
    dual = connections_of(network, ConnectionType.DUAL)
    line = [marker]

    while next_nodes := [t for s, t in dual if s == line[-1] and t not in line]:
        line.append(next_nodes[0])

    distances = [14.0 - network.points[index][1] for index in line]
    assert distances[:4] == pytest.approx([0, 0.5, 1.5, 3.0])
    assert distances[-len(OUTSIDE_NODES) :] == pytest.approx([14 + o for o in OUTSIDE_NODES])
    assert all(network.points[index][0] == 15.0 for index in line)

    # Turn: two forward steps, then reverse back to the end of the dual line.
    reverse = connections_of(network, ConnectionType.REVERSE)
    assert len(reverse) == 1
    turn_end, line_end = next(iter(reverse))
    assert line_end == line[-1]
    assert network.points[turn_end][1] == pytest.approx(-19.7 - 4.4)

    regular = connections_of(network, ConnectionType.REGULAR)
    join = line[-len(OUTSIDE_NODES)]
    entry = next(s for s, t in regular if t == join)
    assert network.points[entry] == pytest.approx((13.8, -1.0))
    exit_ = next(t for s, t in regular if s == line[-2])
    assert network.points[exit_] == pytest.approx((16.7, -16.4))


def test_back_in_lines_connect_all_bays_in_travel_order():
    frame = ShedFrame.from_area(SHED, "front")
    network = plan_parking(frame, settings(exit_left_to_right=False))

    assert [name for _, name in network.markers] == ["Shed 3", "Shed 4", "Shed 5", "Shed 6"]
    assert len(network.open_ends) == 4

    entry_start, entry_end, exit_start, exit_end = network.open_ends
    regular = connections_of(network, ConnectionType.REGULAR)

    def follow(start):
        path = [start]

        while next_nodes := [t for s, t in regular if s == path[-1] and t in on_line]:
            path.append(next_nodes[0])

        return path

    on_line = {i for i, (_, d) in enumerate(network.points) if d == -1.0}
    entry = follow(entry_start)
    assert entry[-1] == entry_end
    assert len(entry) == 6
    # Bays 7.25 m wide; each branch starts 1.2 m before its bay, the ends 5 m beyond.
    assert [network.points[i][0] for i in entry] == pytest.approx(
        [-2.075, 2.925, 10.175, 17.425, 24.675, 29.675]
    )

    on_line = {i for i, (_, d) in enumerate(network.points) if d == pytest.approx(-16.4)}
    exit_ = follow(exit_start)
    assert exit_[-1] == exit_end
    xs = [network.points[i][0] for i in exit_]
    assert xs == sorted(xs, reverse=True)


def test_drive_through_bay_line():
    frame = ShedFrame.from_area(SHED, "front")
    network = plan_parking(
        frame, settings(mode=ParkingMode.DRIVE_THROUGH, bays=1, gaps=(), back_offset=1.0)
    )

    assert {kind for _, _, kind in network.connections} == {ConnectionType.REGULAR}

    marker = network.markers[0][0]
    assert network.points[marker] == pytest.approx((15.0, 14.0))

    line = sorted(
        (i for i, (a, _) in enumerate(network.points) if a == 15.0),
        key=lambda i: network.points[i][1],
    )
    ds = [network.points[i][1] for i in line]
    assert ds[0] == -10 and ds[-1] == 25
    assert max(b - a for a, b in zip(ds, ds[1:], strict=False)) <= 1.6
    assert all(
        (s, t) in connections_of(network, ConnectionType.REGULAR)
        for s, t in zip(line, line[1:], strict=False)
    )


def test_plan_on_the_map_is_rotated_with_the_shed():
    angle = math.radians(30)
    corners = tuple(
        (x * math.cos(angle) - z * math.sin(angle), x * math.sin(angle) + z * math.cos(angle))
        for x, z in SHED.corners
    )
    frame = ShedFrame.from_area(IndoorArea("shed.xml", "1", corners, 0.0), "front")

    assert frame.length == pytest.approx(30)
    assert frame.depth == pytest.approx(15)
    assert frame.to_map(0, 0) == pytest.approx(corners[3])


@pytest.mark.parametrize(
    "values",
    [
        dict(bays=4, gaps=(0.0,)),
        dict(bays=10, gaps=(0.0,) * 9),
        dict(back_offset=15.0),
    ],
)
def test_invalid_settings_are_refused(values):
    with pytest.raises(ValueError):
        plan_parking(ShedFrame.from_area(SHED, "front"), settings(**values))


def test_default_bay_line_is_fitted_to_the_marker_depth():
    line = default_bay_line(14.0)
    distances = line.distances

    assert distances[:4] == pytest.approx([0, 0.5, 1.5, 3.0])
    assert distances[-len(OUTSIDE_NODES) :] == pytest.approx([14 + o for o in OUTSIDE_NODES])
    assert distances[line.entry_node] == pytest.approx(16.3)
    assert line.exit_node == len(distances) - 2
    assert line.turn == TURN_STEPS
    assert line.fits(14.0)


def test_edited_bay_line_is_used_for_every_bay():
    frame = ShedFrame.from_area(SHED, "front")
    line = BayLine((1.0, 2.0, 14.0, 4.0), (2.0,), entry_node=3, exit_node=4)
    network = plan_parking(frame, settings(bays=2, gaps=(0.0,), back_offset=1.0, bay_line=line))

    marker = network.markers[0][0]
    dual = sorted(t for s, t, kind in network.connections if kind == ConnectionType.DUAL)
    depths = [network.points[i][1] for i in [marker, *dual[:4]]]

    assert depths == pytest.approx([14.0, 13.0, 11.0, -3.0, -7.0])
    assert len([1 for *_, kind in network.connections if kind == ConnectionType.REVERSE]) == 2


def test_split_and_remove_keep_the_branches_on_their_nodes():
    line = BayLine((1.0, 2.0, 3.0), (3.2, 1.2), entry_node=2, exit_node=3)

    split = line.split(0)

    assert split.segments == (0.5, 0.5, 2.0, 3.0)
    assert (split.entry_node, split.exit_node) == (3, 4)
    assert split.remove(1) == line
    assert not split.can_remove(0)
    assert not split.can_remove(3)
    assert not split.can_remove(4)

    with pytest.raises(ValueError):
        split.remove(3)


def test_segment_and_turn_lengths_can_be_changed():
    line = BayLine((1.0, 2.0), (3.2, 1.2), entry_node=1, exit_node=2)

    assert line.with_segment(1, 5.0).segments == (1.0, 5.0)
    assert line.with_turn_step(0, 2.0).turn == (2.0, 1.2)


def test_entry_line_stays_outside_the_shed_and_the_branch_before_the_exit_branch():
    line = BayLine((2.0, 2.0, 2.0, 2.0), (1.0,), entry_node=3, exit_node=4)

    # Marker 3 m inside: nodes at 1, -1, -3 and -5 m; the entry line runs 1.3 m inside them.
    assert line.entry_nodes(3.0) == [3]
    assert line.entry_line_depth(3.0) == pytest.approx(-1.7)
    assert line.exit_nodes() == [4]
    assert line.fits(3.0)
    assert not line.fits(5.0)

    with pytest.raises(ValueError):
        plan_parking(
            ShedFrame.from_area(SHED, "front"),
            settings(bays=1, gaps=(), back_offset=9.0, bay_line=line),
        )


def test_drive_through_line_has_the_marker_before_the_exit_side():
    frame = ShedFrame.from_area(SHED, "front")
    depths, marker = drive_through_line(frame, settings(back_offset=1.0))

    assert depths[0] == -10 and depths[-1] == 25
    assert depths[marker] == pytest.approx(14.0)


def test_a_template_keeps_the_layout_but_not_directions_and_names():
    line = default_bay_line(10.0).split(0)
    original = settings(
        mode=ParkingMode.DRIVE_THROUGH, open_side="left", gaps=(0.1, 0.2, 0.3), bay_line=line
    )
    original = replace(original, entry_left_to_right=False, back_offset=3.5)

    restored = from_template(template_values(original))

    assert restored == replace(
        original, entry_left_to_right=True, marker_name="", start_number=1, group=""
    )


def test_a_template_without_edited_bay_line_keeps_it_fitted():
    assert from_template(template_values(settings())).bay_line is None


@pytest.mark.parametrize(
    "change",
    [
        {"mode": "fly"},
        {"open_side": "top"},
        {"gaps": [0.0]},
        {"bays": None},
        {"bay_line": {"segments": [1.0], "turn": [], "entry_node": 1, "exit_node": 3}},
    ],
)
def test_unusable_templates_are_rejected(change):
    with pytest.raises(ValueError):
        from_template(template_values(settings()) | change)
