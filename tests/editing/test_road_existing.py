import math

from road_lane_helpers import junction, lane

from autodrive_editor.editing.edit_history import EditHistory
from autodrive_editor.editing.planned_piece import push_piece
from autodrive_editor.editing.road_existing import fit_to_existing, mostly_two_way
from autodrive_editor.editing.road_graph import build_road_graph
from autodrive_editor.editing.road_network import RoadOptions, build_road_network
from autodrive_editor.model.autodrive_data import SUBPRIO_FLAG, AutoDriveData, MarkerData, NodeData
from autodrive_editor.model.connections import (
    CONNECTION_STATES,
    ConnectionType,
    write_connection_state,
)

ROAD = [lane((0, 2), (100, 2)), lane((100, -2), (0, -2))]
EAST, WEST = 2.75, -2.75  # the planned lanes (lane gap 5.5)


def plan(lanes=ROAD, **options):
    return build_road_network(build_road_graph(lanes), RoadOptions(**options))


def pushed(data, piece):
    push_piece(EditHistory(), data, piece, "Create")
    return data


def chain(data, points, kind=ConnectionType.REGULAR, flag=0):
    first = max(data.nodes, default=0) + 1
    for k, (x, z) in enumerate(points):
        data.add_node(NodeData(first + k, x, 0, z, flag))
    for a in range(first, first + len(points) - 1):
        write_connection_state(data, a, a + 1, CONNECTION_STATES[kind])
    return list(range(first, first + len(points)))


def arm_ends(angle):
    a = math.radians(angle)
    return [
        (100 * math.cos(a) - s * math.sin(a), 100 * math.sin(a) + s * math.cos(a))
        for s in (EAST, WEST)
    ]


def node_at(data, x, z):
    return min(data.nodes, key=lambda i: math.dist((x, z), (data.nodes[i].x, data.nodes[i].z)))


def reaches(data, start, goal):
    seen, todo = {start}, [start]
    while todo:
        n = todo.pop()
        for m in data.nodes[n].outgoing:
            if n in data.nodes[m].incoming and m not in seen:
                seen.add(m)
                todo.append(m)
    return goal in seen


def test_road_already_in_the_network_is_left_out():
    data = pushed(AutoDriveData(), plan().piece)

    result = fit_to_existing(plan(), data, replace=False, gap=5.5)

    assert not result.piece.points and not result.piece.joins


def only_near(data, keep):
    """The data with only the nodes for which keep(node) is true."""
    for i in [i for i, n in data.nodes.items() if not keep(n)]:
        del data.nodes[i]
    for n in data.nodes.values():
        n.incoming &= set(data.nodes)
        n.outgoing &= set(data.nodes)
    return data


def test_skip_fills_the_gap_and_joins_the_existing_lanes():
    data = only_near(pushed(AutoDriveData(), plan().piece), lambda n: n.x < 50)

    result = fit_to_existing(plan(), data, replace=False, gap=5.5)
    pushed(data, result.piece)

    points = [(n.x, n.z) for n in data.nodes.values()]
    assert all(math.dist(p, q) > 1 for k, p in enumerate(points) for q in points[:k])
    assert reaches(data, node_at(data, 0, EAST), node_at(data, 100, EAST))
    assert reaches(data, node_at(data, 100, WEST), node_at(data, 0, WEST))
    assert not result.listed


def test_two_way_lane_keeps_the_direction_an_existing_one_way_lane_lacks():
    data = AutoDriveData()
    chain(data, [(x, 0) for x in range(0, 101, 10)])

    result = fit_to_existing(plan(two_way=True), data, replace=False, gap=5.5)

    connections = result.piece.connections
    assert connections and {kind for _, _, kind in connections} == {ConnectionType.REGULAR}
    assert all(result.piece.points[a][0] > result.piece.points[b][0] for a, b, _ in connections)
    assert len(result.piece.joins) <= 2


def test_subprio_lane_along_the_road_does_not_count():
    data = AutoDriveData()
    chain(data, [(x, EAST) for x in range(0, 101, 10)], flag=SUBPRIO_FLAG)

    result = fit_to_existing(plan(), data, replace=False, gap=5.5)

    assert len(result.piece.points) == len(plan().piece.points) and not result.piece.joins


def test_existing_connection_is_split_where_no_node_fits():
    data = AutoDriveData()
    ids = chain(data, [(x, 0) for x in range(0, 51, 10)], ConnectionType.DUAL)
    for i in ids:
        data.markers[i] = MarkerData(i, f"M{i}", "All")

    result = fit_to_existing(plan(two_way=True), data, replace=False, gap=5.5)
    pushed(data, result.piece)

    assert result.piece.cut
    assert reaches(data, ids[0], node_at(data, 100, 0))
    assert reaches(data, node_at(data, 100, 0), ids[0])


def test_existing_junction_is_kept_and_every_arm_joins_it():
    lanes = junction((0, 90, 180))
    data = only_near(
        pushed(AutoDriveData(), plan(lanes).piece), lambda n: math.hypot(n.x, n.z) < 15
    )
    box = set(data.nodes)

    result = fit_to_existing(plan(lanes), data, replace=False, gap=5.5)
    pushed(data, result.piece)

    assert all(math.dist(p[::2], (0, 0)) > 8 for p in result.piece.points)
    assert len(result.listed) == 1
    arms = [[node_at(data, x, z) for x, z in arm_ends(angle)] for angle in (0, 90, 180)]
    assert not box & result.piece.removed
    for k, arm in enumerate(arms):
        (entry,) = [n for n in arm if data.nodes[n].outgoing]
        exits = [
            n for other in arms[:k] + arms[k + 1 :] for n in other if not data.nodes[n].outgoing
        ]
        assert len(exits) == 2 and all(reaches(data, entry, n) for n in exits)


def test_replace_removes_the_old_road_and_joins_its_branch_and_marker():
    data = AutoDriveData()
    old = chain(data, [(x, 0) for x in range(0, 101, 10)], ConnectionType.DUAL)
    branch = chain(data, [(50, 40), (50, 20)], ConnectionType.DUAL)
    write_connection_state(data, branch[1], old[5], CONNECTION_STATES[ConnectionType.DUAL])
    data.markers[old[5]] = MarkerData(old[5], "Shop", "All")

    result = fit_to_existing(plan(), data, replace=True, gap=5.5)
    pushed(data, result.piece)

    assert not set(old) & set(data.nodes)
    assert [m.name for m in data.markers.values()] == ["Shop"]
    assert abs(abs(data.nodes[next(iter(data.markers))].z) - EAST) < 0.1
    for x, z in ((0, WEST), (100, EAST)):
        assert reaches(data, branch[0], node_at(data, x, z))
        assert reaches(data, node_at(data, 100 - x, z), branch[0])
    assert not result.listed


def test_mostly_two_way_counts_regular_connections():
    data = AutoDriveData()
    assert not mostly_two_way(data)  # empty: one-way lanes
    chain(data, [(0, 0), (10, 0), (20, 0)], ConnectionType.DUAL)
    chain(data, [(0, 5), (10, 5)])
    assert mostly_two_way(data)
    chain(data, [(0, 9), (10, 9), (20, 9)])
    assert not mostly_two_way(data)
    chain(data, [(0, 20), (10, 20), (20, 20)], ConnectionType.DUAL, flag=SUBPRIO_FLAG)
    assert not mostly_two_way(data)  # subprio does not count
