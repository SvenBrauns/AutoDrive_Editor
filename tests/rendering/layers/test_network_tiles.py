from autodrive_editor.model.autodrive_data import SUBPRIO_FLAG, AutoDriveData, NodeData
from autodrive_editor.model.connections import ConnectionType
from autodrive_editor.rendering.layers.network_tiles import NetworkTiles
from autodrive_editor.rendering.spatial.connection_index import ConnectionSpatialIndex
from autodrive_editor.rendering.spatial.node_index import NodeSpatialIndex

TILE = 100.0


def build(*nodes):
    data = AutoDriveData()

    for node in nodes:
        data.add_node(node)

    node_index = NodeSpatialIndex(tile_size=TILE)
    connection_index = ConnectionSpatialIndex(tile_size=TILE)
    node_index.build(data)
    connection_index.build(data)

    tiles = NetworkTiles(node_index, connection_index)
    tiles.refresh()

    return data, node_index, connection_index, tiles


def test_dual_connection_is_drawn_once_and_can_get_arrows(qapp):
    _, _, _, tiles = build(
        NodeData(1, 0, 0, 0, outgoing={2}, incoming={2}),
        NodeData(2, 10, 0, 0, outgoing={1}, incoming={1}),
    )

    (tile,) = tiles.connection_tiles.values()

    assert tile.paths[ConnectionType.DUAL].elementCount() == 2  # one moveTo, one lineTo
    assert tile.arrows == [(10, 0, 0, 10, 0, ConnectionType.DUAL)]


def test_arrow_connections_are_sorted_longest_first(qapp):
    _, _, _, tiles = build(
        NodeData(1, 0, 0, 0, outgoing={2, 3}),
        NodeData(2, 5, 0, 0, incoming={1}),
        NodeData(3, 30, 0, 0),
    )

    (tile,) = tiles.connection_tiles.values()

    assert [(entry[0], entry[5]) for entry in tile.arrows] == [
        (30, ConnectionType.REVERSE),
        (5, ConnectionType.REGULAR),
    ]


def test_nodes_are_split_by_type(qapp):
    _, _, _, tiles = build(NodeData(1, 0, 0, 0), NodeData(2, 5, 0, 0, flag=SUBPRIO_FLAG))

    (tile,) = tiles.node_tiles.values()

    assert (tile.regular.size(), tile.subprio.size()) == (1, 1)


def test_only_changed_tiles_are_rebuilt(qapp):
    data, node_index, connection_index, tiles = build(
        NodeData(1, 10, 0, 10, outgoing={2}),
        NodeData(2, 20, 0, 10, incoming={1}),
        NodeData(3, 510, 0, 10),
    )
    far_tile = tiles.node_tiles[(5, 0)]

    data.nodes[2].x = 30
    node_index.update_nodes([data.nodes[2]])
    connection_index.update_node_positions(data, [2])
    tiles.refresh()

    assert tiles.node_tiles[(5, 0)] is far_tile
    assert tiles.node_tiles[(0, 0)].regular.at(1).x() in (10, 30)
    assert tiles.connection_tiles[(0, 0)].arrows[0][3] == 30


def test_emptied_tiles_are_dropped(qapp):
    _, node_index, _, tiles = build(NodeData(1, 10, 0, 10), NodeData(2, 510, 0, 10))

    node_index.remove_nodes({2})
    tiles.refresh()

    assert list(tiles.node_tiles) == [(0, 0)]


def test_tiles_are_found_by_area(qapp):
    from PySide6.QtCore import QRectF

    _, _, _, tiles = build(NodeData(1, 10, 0, 10), NodeData(2, 510, 0, 10))

    assert len(tiles.get_node_tiles(QRectF(0, 0, 50, 50))) == 1
    assert len(tiles.get_node_tiles(QRectF(0, 0, 600, 50))) == 2
