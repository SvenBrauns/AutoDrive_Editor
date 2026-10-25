import pytest
from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QPainterPath, QPolygonF

from autodrive_editor.model.autodrive_data import AutoDriveData, NodeData
from autodrive_editor.rendering.spatial.node_index import NodeSpatialIndex


def build_index(positions, tile_size=100.0):
    data = AutoDriveData()

    for node_id, (x, z) in enumerate(positions, start=1):
        data.add_node(NodeData(node_id=node_id, x=x, y=0.0, z=z))

    index = NodeSpatialIndex(tile_size=tile_size)
    index.build(data)
    return index


def ids(nodes):
    return sorted(node.node_id for node in nodes)


def test_rejects_non_positive_tile_size():
    with pytest.raises(ValueError):
        NodeSpatialIndex(tile_size=0)


def test_build_counts_nodes():
    index = build_index([(0, 0), (500, 500), (-500, -500)])

    assert index.node_count == 3


def test_rect_query_returns_only_nodes_inside():
    index = build_index([(10, 10), (150, 10), (10, 150), (-50, -50)])

    result = index.get_nodes_in_rect(QRectF(0, 0, 100, 100))

    assert ids(result) == [1]


def test_rect_query_spans_multiple_tiles_including_negative():
    index = build_index([(-150, -150), (50, 50), (250, 250), (1000, 1000)])

    result = index.get_nodes_in_rect(QRectF(-200, -200, 500, 500))

    assert ids(result) == [1, 2, 3]


def test_padding_extends_query():
    index = build_index([(110, 50)])

    assert index.get_nodes_in_rect(QRectF(0, 0, 100, 100)) == []
    assert ids(index.get_nodes_in_rect(QRectF(0, 0, 100, 100), padding=20)) == [1]


def test_empty_rect_returns_nothing():
    index = build_index([(0, 0)])

    assert index.get_nodes_in_rect(QRectF()) == []


def test_rebuild_replaces_previous_nodes():
    index = build_index([(0, 0), (10, 10)])

    index.build(AutoDriveData())

    assert index.node_count == 0
    assert index.get_nodes_in_rect(QRectF(-1000, -1000, 2000, 2000)) == []


def test_path_query_uses_exact_shape_not_bounding_box():
    # Triangle covering the lower-left half of a 100 x 100 square.
    index = build_index([(10, 80), (80, 10)])

    path = QPainterPath()
    path.addPolygon(QPolygonF([QPointF(0, 0), QPointF(0, 100), QPointF(100, 100)]))
    path.closeSubpath()

    assert ids(index.get_nodes_in_path(path)) == [1]


def test_update_nodes_moves_node_to_new_tile():
    data = AutoDriveData()
    data.add_node(NodeData(node_id=1, x=10, y=0, z=10))
    data.add_node(NodeData(node_id=2, x=20, y=0, z=20))
    index = NodeSpatialIndex(tile_size=100.0)
    index.build(data)

    data.nodes[1].x, data.nodes[1].z = 550, 550
    index.update_nodes([data.nodes[1]])

    assert ids(index.get_nodes_in_rect(QRectF(0, 0, 100, 100))) == [2]
    assert ids(index.get_nodes_in_rect(QRectF(500, 500, 100, 100))) == [1]
    assert index.node_count == 2


def test_update_nodes_ignores_unknown_nodes():
    index = build_index([(0, 0)])

    index.update_nodes([NodeData(node_id=99, x=5, y=0, z=5)])

    assert index.get_nodes_in_rect(QRectF(0, 0, 100, 100))[0].node_id == 1


def test_empty_path_returns_nothing():
    index = build_index([(0, 0)])

    assert index.get_nodes_in_path(QPainterPath()) == []


def test_remove_and_add_nodes():
    data = AutoDriveData()
    data.add_node(NodeData(node_id=1, x=10, y=0, z=10))
    data.add_node(NodeData(node_id=2, x=20, y=0, z=20))
    index = NodeSpatialIndex(tile_size=100.0)
    index.build(data)

    index.remove_nodes([1, 99])
    assert ids(index.get_nodes_in_rect(QRectF(0, 0, 100, 100))) == [2]
    assert index.node_count == 1

    index.add_nodes([data.nodes[1]])
    assert ids(index.get_nodes_in_rect(QRectF(0, 0, 100, 100))) == [1, 2]
    assert index.node_count == 2
