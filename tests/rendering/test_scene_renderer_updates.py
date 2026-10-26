import pytest
from drawing_helpers import ORANGE, RED, paint_scene
from PySide6.QtWidgets import QGraphicsScene

from autodrive_editor.model.autodrive_data import SUBPRIO_FLAG, AutoDriveData, MarkerData, NodeData
from autodrive_editor.paths import MARKER_ICON_PATH
from autodrive_editor.rendering.scene_renderer import SceneRenderer

WHITE = "#ffffff"


@pytest.fixture
def renderer(qapp):
    data = AutoDriveData()
    data.add_node(NodeData(node_id=1, x=0, y=0, z=0, outgoing={2}))
    data.add_node(NodeData(node_id=2, x=50, y=0, z=0, incoming={1}))
    data.add_marker(MarkerData(node_id=1, name="Hof"))

    scene_renderer = SceneRenderer(QGraphicsScene(), MARKER_ICON_PATH)
    scene_renderer.render(data)

    yield scene_renderer

    scene_renderer.reset()


def paint(renderer, center, scale=4.0):
    return paint_scene(renderer.scene, center, scale)


def drawn_connections(renderer):
    renderer.tiles.refresh()

    return sorted(
        (source_x, source_z, target_x, target_z)
        for tile in renderer.tiles.connection_tiles.values()
        for _, source_x, source_z, target_x, target_z, _ in tile.one_way
    )


def move_node(renderer, node_id, x, z):
    node = renderer.autodrive_data.nodes[node_id]
    node.x, node.z = x, z
    renderer.update_node_positions({node_id})


def delete_node(renderer, node_id):
    data = renderer.autodrive_data
    node = data.nodes.pop(node_id)
    data.markers.pop(node_id, None)
    neighbors = set()
    for other in data.nodes.values():
        for attribute in ("incoming", "outgoing"):
            if node_id in getattr(other, attribute):
                getattr(other, attribute).discard(node_id)
                neighbors.add(other.node_id)
    renderer.apply_changes(removed_node_ids={node_id}, connection_node_ids=neighbors)
    return node


def test_nodes_are_drawn_where_they_are(renderer):
    assert paint(renderer, (0, 0)).color_at(0, 0) == RED


def test_moved_node_is_drawn_at_its_new_place(renderer):
    move_node(renderer, 2, 80, 40)

    assert paint(renderer, (80, 40)).color_at(80, 40) == RED
    assert paint(renderer, (50, 0)).color_at(50, 0) != RED
    assert drawn_connections(renderer) == [(0, 0, 80, 40)]


def test_flag_change_redraws_the_node(renderer):
    renderer.autodrive_data.nodes[1].flag = SUBPRIO_FLAG
    renderer.apply_changes(changed_flag_node_ids={1})

    assert paint(renderer, (0, 0)).color_at(0, 0) == ORANGE


def test_nodes_fade_out_when_zoomed_out(renderer):
    assert paint(renderer, (0, 0), scale=0.2).color_at(0, 0) != RED


def test_selected_nodes_stay_visible_when_zoomed_out(renderer):
    renderer.set_selected_node_ids({1})

    painted = paint(renderer, (0, 0), scale=0.2)

    assert painted.color_at(0, 0) == RED
    assert paint(renderer, (50, 0), scale=0.2).color_at(50, 0) != RED


def test_selection_follows_the_node(renderer):
    renderer.set_selected_node_ids({1})

    move_node(renderer, 1, 10, 20)

    assert paint(renderer, (10, 20), scale=0.2).color_at(10, 20) == RED


def test_removed_node_loses_drawing_selection_and_connections(renderer):
    renderer.set_selected_node_ids({1})

    delete_node(renderer, 1)

    assert paint(renderer, (0, 0)).color_at(0, 0) == WHITE
    assert drawn_connections(renderer) == []
    assert renderer.selected_node_ids == set()
    assert renderer.node_spatial_index.node_count == 1


def test_re_added_node_gets_drawing_and_connections_back(renderer):
    node = delete_node(renderer, 2)

    data = renderer.autodrive_data
    data.add_node(node)
    data.nodes[1].outgoing.add(2)
    renderer.apply_changes(added_node_ids={2}, connection_node_ids={1})

    assert paint(renderer, (50, 0)).color_at(50, 0) == RED
    assert drawn_connections(renderer) == [(0, 0, 50, 0)]


def test_layers_grow_with_nodes_moved_outside(renderer):
    move_node(renderer, 2, 5000, 0)

    assert renderer.connection_layer.boundingRect().contains(5000, 0)
    assert paint(renderer, (5000, 0)).color_at(5000, 0) == RED


def test_reset_forgets_data(renderer):
    renderer.reset()

    renderer.update_node_positions({1})  # must not fail without data

    assert renderer.autodrive_data is None
    assert renderer.layers == []


@pytest.mark.parametrize("zoom", [2.0, 4.0, 40.0])
def test_node_is_found_on_its_dot(renderer, zoom):
    assert renderer.get_node_at(0.5 / zoom, 0, zoom).node_id == 1


def test_far_point_finds_no_node(renderer):
    assert renderer.get_node_at(25, 0, 4.0) is None


def test_hidden_nodes_cannot_be_clicked_but_selected_ones_can(renderer):
    assert renderer.get_node_at(0, 0, 0.1) is None

    renderer.set_selected_node_ids({1})

    assert renderer.get_node_at(0, 0, 0.1).node_id == 1


def test_closest_node_wins(renderer):
    move_node(renderer, 2, 1, 0)

    assert renderer.get_node_at(0.8, 0, 4.0).node_id == 2
