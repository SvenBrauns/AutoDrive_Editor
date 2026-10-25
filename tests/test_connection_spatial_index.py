from PySide6.QtCore import QRectF

from autodrive.models import AutoDriveData, NodeData
from rendering.connection_data import ConnectionType
from rendering.connection_spatial_index import ConnectionSpatialIndex


def build_data():
    # 1 -> 2 regular, 2 <-> 3 dual
    data = AutoDriveData()
    data.add_node(NodeData(node_id=1, x=0, y=0, z=0, outgoing={2}))
    data.add_node(NodeData(node_id=2, x=50, y=0, z=0, incoming={1, 3}, outgoing={3}))
    data.add_node(NodeData(node_id=3, x=100, y=0, z=0, incoming={2}, outgoing={2}))
    return data


def build_index(data):
    index = ConnectionSpatialIndex(tile_size=100.0)
    index.build(data)
    return index


def everything():
    return QRectF(-10_000, -10_000, 20_000, 20_000)


def test_dual_connection_is_stored_once():
    index = build_index(build_data())

    types = sorted(c.connection_type.value for c in index.get_connections_in_rect(everything()))

    assert index.connection_count == 2
    assert types == [ConnectionType.DUAL.value, ConnectionType.REGULAR.value]


def test_update_node_positions_moves_connections():
    data = build_data()
    index = build_index(data)

    data.nodes[1].x, data.nodes[1].z = 500, 500
    index.update_node_positions(data, [1])

    far_away = index.get_connections_in_rect(QRectF(450, 450, 100, 100))
    assert [(c.source_id, c.target_id) for c in far_away] == [(1, 2)]
    assert (far_away[0].source_x, far_away[0].source_z) == (500, 500)


def test_moved_connection_leaves_old_tiles():
    data = build_data()
    index = build_index(data)

    data.nodes[1].x, data.nodes[1].z = 1000, 1000
    data.nodes[2].x, data.nodes[2].z = 1050, 1000
    index.update_node_positions(data, [1, 2])

    near_origin = index.get_connections_in_rect(QRectF(-10, -10, 40, 20))
    assert near_origin == []


def test_update_keeps_connection_count_and_type():
    data = build_data()
    index = build_index(data)

    data.nodes[3].x = 300
    index.update_node_positions(data, [3])

    connections = index.get_connections_in_rect(everything())
    assert index.connection_count == 2
    dual = [c for c in connections if c.connection_type == ConnectionType.DUAL]
    assert len(dual) == 1
    assert max(dual[0].source_x, dual[0].target_x) == 300


def test_update_ignores_nodes_without_connections():
    data = build_data()
    data.add_node(NodeData(node_id=4, x=0, y=0, z=0))
    index = build_index(data)

    index.update_node_positions(data, [4, 99])

    assert index.connection_count == 2


def connection_pairs(index):
    return sorted(
        (c.connection_type.value, min(c.source_id, c.target_id), max(c.source_id, c.target_id))
        for c in index.get_connections_in_rect(everything())
    )


def test_rebuild_removes_connections_of_deleted_node():
    data = build_data()
    index = build_index(data)

    del data.nodes[2]
    data.nodes[1].outgoing.discard(2)
    data.nodes[3].incoming.discard(2)
    data.nodes[3].outgoing.discard(2)
    index.rebuild_node_connections(data, {2, 1, 3})

    assert index.connection_count == 0
    assert connection_pairs(index) == []


def test_rebuild_restores_connections_of_re_added_node():
    data = build_data()
    index = build_index(data)
    before = connection_pairs(index)
    node_2 = data.nodes.pop(2)
    index.rebuild_node_connections(data, {2})

    data.nodes[2] = node_2
    index.rebuild_node_connections(data, {2, 1, 3})

    assert connection_pairs(index) == before
    assert index.connection_count == 2


def test_rebuild_finds_one_way_reverse_connection_from_source():
    # 4 -> 2 is stored only in 4.outgoing
    data = build_data()
    data.add_node(NodeData(node_id=4, x=50, y=0, z=50, outgoing={2}))
    index = build_index(data)
    assert ("reverse", 2, 4) in connection_pairs(index)

    index.rebuild_node_connections(data, {4})

    assert ("reverse", 2, 4) in connection_pairs(index)
    assert index.connection_count == 3


def test_moving_after_rebuild_keeps_index_consistent():
    data = build_data()
    index = build_index(data)
    index.rebuild_node_connections(data, {1, 2, 3})

    data.nodes[1].x = 400
    index.update_node_positions(data, [1])

    assert index.connection_count == 2
    assert len(index.get_connections_in_rect(everything())) == 2
