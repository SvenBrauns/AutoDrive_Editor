from PySide6.QtCore import QRectF

from autodrive_editor.model.autodrive_data import AutoDriveData, NodeData
from autodrive_editor.rendering.connections.connection_data import ConnectionType
from autodrive_editor.rendering.spatial.connection_index import ConnectionSpatialIndex


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


def test_rebuild_keeps_one_way_connection_into_rebuilt_node():
    # 4 -> 2 is reverse: only 4.outgoing knows about it. Rebuilding
    # node 2 alone must still keep it.
    data = build_data()
    data.add_node(NodeData(node_id=4, x=50, y=0, z=50, outgoing={2}))
    index = build_index(data)

    index.rebuild_node_connections(data, {2})

    assert ("reverse", 2, 4) in connection_pairs(index)
    assert index.connection_count == 3


def test_incremental_updates_match_a_fresh_build():
    """Random connection edits: the incrementally updated index must
    always equal an index built from scratch."""
    import random

    from autodrive_editor.editing.commands.set_connection import (
        CONNECTION_STATES,
        NO_CONNECTION,
        SetConnectionCommand,
    )

    rng = random.Random(7)
    data = AutoDriveData()
    for node_id in range(1, 9):
        data.add_node(NodeData(node_id=node_id, x=node_id * 30.0, y=0, z=(node_id % 3) * 30.0))
    index = build_index(data)
    states = list(CONNECTION_STATES.values()) + [NO_CONNECTION]

    for _ in range(120):
        source, target = rng.sample(range(1, 9), 2)
        command = SetConnectionCommand(data, source, target, rng.choice(states))
        command.redo()
        index.rebuild_node_connections(data, {source, target})

        assert connection_pairs(index) == connection_pairs(build_index(data))
