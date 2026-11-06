from road_lane_helpers import junction

from autodrive_editor.editing.road_graph import build_road_graph
from autodrive_editor.editing.road_network import build_road_network
from autodrive_editor.editing.road_selection import box_part, road_at, road_part

# A T junction at the origin, arms 150 m long to the east, north (+z) and west.
GRAPH = build_road_graph(junction([0, 90, 180], arm_length=150))
NETWORK = build_road_network(GRAPH)
POINTS = NETWORK.piece.points


def square(x0, z0, x1, z1):
    return [(x0, z0), (x1, z0), (x1, z1), (x0, z1)]


def test_a_box_keeps_the_junction_whose_middle_is_inside_it_whole():
    part = box_part(NETWORK, GRAPH, square(-60, -60, 60, 60))
    kept = [POINTS[i] for i in part.keep]

    assert part.network.groups == NETWORK.groups
    assert kept and all(max(abs(p[0]), abs(p[2])) < 65 for p in kept)
    assert any(abs(p[0]) < 10 and abs(p[2]) < 10 for p in kept)
    # Cut off at the box edge on each arm.
    assert part.edges and all(max(abs(p[0]), abs(p[2])) > 45 for p in part.edges)


def test_a_box_leaves_out_a_junction_whose_middle_is_outside():
    part = box_part(NETWORK, GRAPH, square(5, -60, 160, 60))
    kept = [POINTS[i] for i in part.keep]

    assert part.network.groups == [] and part.network.listed == []
    assert kept and all(p[0] > 12 for p in kept)  # the junction box ends at x = 9.75


def test_a_clicked_road_runs_to_the_junction_without_it():
    part = road_part(NETWORK, GRAPH, road_at(GRAPH, 100.0, 2.0, reach=10.0))
    kept = [POINTS[i] for i in part.keep]

    assert part.network.groups == []
    assert kept and all(p[0] > 15 and abs(p[2]) < 5 for p in kept)
    assert max(p[0] for p in kept) > 140
    assert road_at(GRAPH, 100.0, 80.0, reach=10.0) is None
