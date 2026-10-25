import pytest

from PySide6.QtCore import QRectF
from PySide6.QtWidgets import QGraphicsScene

from app_paths import MARKER_ICON_PATH
from autodrive.models import AutoDriveData, MarkerData, NodeData
from rendering.scene_renderer import SceneRenderer


VISIBLE_RECT = QRectF(-100, -100, 300, 200)


@pytest.fixture
def renderer(qapp):
    data = AutoDriveData()
    data.add_node(NodeData(node_id=1, x=0, y=0, z=0, outgoing={2}))
    data.add_node(NodeData(node_id=2, x=50, y=0, z=0, incoming={1}))
    data.add_marker(MarkerData(node_id=1, name="Hof"))

    scene = QGraphicsScene()
    scene_renderer = SceneRenderer(scene, MARKER_ICON_PATH)
    scene_renderer.render(data)
    scene_renderer.update_visibility_for_zoom(2.0)   # detail view, nodes visible
    scene_renderer.update_visible_scene_rect(VISIBLE_RECT)
    scene_renderer.set_selected_node_ids({1})

    yield scene_renderer

    scene_renderer.reset()


def move_node(renderer, node_id, x, z):
    node = renderer.autodrive_data.nodes[node_id]
    node.x, node.z = x, z
    renderer.update_node_positions({node_id})


def test_node_marker_and_selection_items_follow_the_node(renderer):
    marker_item = renderer.visible_marker_manager.visible_marker_items[1]
    marker_offset = marker_item.pos()

    move_node(renderer, 1, 10, 20)

    assert renderer.visible_node_manager.visible_node_items[1].pos().toTuple() == (10, 20)
    assert renderer.visible_node_selection_manager.visible_selection_items[1].pos().toTuple() == (10, 20)
    assert (marker_item.pos() - marker_offset).toTuple() == pytest.approx((10, 20))


def test_node_moved_out_of_view_loses_its_item(renderer):
    move_node(renderer, 2, 5000, 5000)

    assert 2 not in renderer.visible_node_manager.visible_node_items


def test_node_moved_into_view_gets_an_item(renderer):
    move_node(renderer, 2, 5000, 5000)
    move_node(renderer, 2, 60, 0)

    assert renderer.visible_node_manager.visible_node_items[2].pos().toTuple() == (60, 0)


def test_detail_connections_follow_the_node(renderer):
    move_node(renderer, 2, 80, 40)

    connections = renderer.connection_spatial_index.get_connections_in_rect(VISIBLE_RECT)
    assert [(c.target_x, c.target_z) for c in connections] == [(80, 40)]


def test_overview_is_rebuilt_when_shown(renderer):
    move_node(renderer, 2, 80, 40)
    assert renderer.overview_connections_outdated

    renderer.update_visibility_for_zoom(0.1)   # switch to the overview

    assert not renderer.overview_connections_outdated
    assert all(item.isVisible() for item in renderer.connection_items.values())


def test_reset_forgets_data(renderer):
    renderer.reset()

    renderer.update_node_positions({1})   # must not fail without data

    assert renderer.autodrive_data is None
