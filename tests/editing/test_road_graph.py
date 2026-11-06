import pytest
from road_lane_helpers import circle, junction, lane, roundabout, two_way_circle

from autodrive_editor.editing.road_graph import build_road_graph


def test_lanes_joined_end_to_start_form_one_stretch():
    graph = build_road_graph(
        [lane((0, 0), (50, 0)), lane((50.1, 0), (100, 0)), lane((100, 0), (150, 0))]
    )

    assert len(graph.stretches) == 1
    assert graph.stretches[0].points[0] == (0, 0, 0) and graph.stretches[0].points[-1] == (
        150,
        0,
        0,
    )
    assert graph.stretches[0].start is None and graph.stretches[0].end is None
    assert graph.junctions == ()


def test_two_way_road_has_no_junction():
    graph = build_road_graph([lane((0, 2), (100, 2)), lane((100, -2), (0, -2))])

    assert len(graph.stretches) == 2 and graph.junctions == ()


@pytest.mark.parametrize(
    "angles", [(0, 90, 180), (0, 90, 180, 270), (90, 210, 330)], ids=["T", "cross", "Y"]
)
def test_junction_with_turn_lanes(angles):
    graph = build_road_graph(junction(angles))

    assert len(graph.junctions) == 1
    j = graph.junctions[0]
    arms = len(angles)
    assert len(j.inner) == arms * (arms - 1)
    assert len(j.moves) == arms * (arms - 1)
    assert not j.crossing and not j.roundabout and not graph.has_crossings
    roads = [s for i, s in enumerate(graph.stretches) if i not in j.inner]
    assert len(roads) == 2 * arms
    assert all((s.start == 0) != (s.end == 0) for s in roads)
    for a, b in j.moves:
        assert graph.stretches[a].end == 0 and graph.stretches[b].start == 0


def test_slip_road_forks_off_one_lane():
    graph = build_road_graph(
        [
            lane((0, 2), (100, 2)),
            lane((100, 2), (200, 2)),
            lane((100, 2), (150, 30), (200, 60)),
            lane((200, -2), (0, -2)),
        ]
    )

    assert len(graph.junctions) == 1
    j = graph.junctions[0]
    assert j.inner == frozenset() and len(j.moves) == 2
    (into,) = {a for a, _ in j.moves}
    assert graph.stretches[into].points[0] == (0, 0, 2)
    assert sum(s.start is None and s.end is None for s in graph.stretches) == 1  # the other lane


def test_roundabout():
    graph = build_road_graph(roundabout((0, 90, 180, 270)))

    assert len(graph.junctions) == 1
    j = graph.junctions[0]
    assert j.roundabout and len(j.inner) == 8
    assert len(j.moves) == 16  # every entry to every exit, turning back included


def test_two_way_loops_crossing():
    graph = build_road_graph([*two_way_circle((0, 0), 200), *two_way_circle((300, 0), 200)])

    assert len(graph.junctions) == 2 and graph.has_crossings
    for j in graph.junctions:
        assert j.crossing and not j.roundabout
        assert len(j.moves) == 4  # straight on, each lane
        for a, b in j.moves:
            assert graph.stretches[a].end == graph.stretches[b].start == graph.junctions.index(j)


def test_one_way_loop_alone_stays_closed():
    graph = build_road_graph([circle((0, 0), 100)])

    assert len(graph.stretches) == 1 and graph.junctions == ()
    assert graph.stretches[0].points[0] == pytest.approx(graph.stretches[0].points[-1])


@pytest.mark.parametrize(("height", "junctions"), [(8.0, 0), (1.0, 1)], ids=["bridge", "level"])
def test_lanes_crossing_are_a_junction_only_at_the_same_level(height, junctions):
    graph = build_road_graph([lane((0, 0), (100, 0)), lane((50, -50), (50, 50), height=height)])

    assert len(graph.junctions) == junctions
    assert len(graph.stretches) == 2 + 2 * junctions


def test_turn_lanes_forking_off_far_from_the_middle_make_one_junction():
    graph = build_road_graph(junction((0, 90, 180), inner_radius=50, arm_length=400))

    assert len(graph.junctions) == 1 and not graph.has_crossings
    assert len(graph.junctions[0].moves) == 6


def test_junctions_joined_by_a_short_road_stay_apart():
    lanes = [
        *junction((90, 180, 270, 0), arm_length={90: 300, 180: 300, 270: 300, 0: 30}),
        *junction(
            (90, 180, 270, 0), arm_length={90: 300, 180: 30, 270: 300, 0: 300}, centre=(60, 0)
        ),
    ]

    graph = build_road_graph(lanes)

    assert len(graph.junctions) == 2
