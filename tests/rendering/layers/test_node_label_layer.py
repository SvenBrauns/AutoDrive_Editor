"""Node ID labels on the map."""

from drawing_helpers import paint_scene
from PySide6.QtWidgets import QGraphicsScene

from autodrive_editor.model.autodrive_data import AutoDriveData, NodeData
from autodrive_editor.paths import MARKER_ICON_PATH
from autodrive_editor.rendering.display_style import DisplayStyle
from autodrive_editor.rendering.scene_renderer import SceneRenderer
from autodrive_editor.rendering.visibility import Visibility

ZOOM = DisplayStyle().node_id_min_zoom


def render_nodes(*positions, visibility=None):
    visibility = visibility or Visibility(node_ids=True)
    data = AutoDriveData()

    for node_id, x in positions:
        data.add_node(NodeData(node_id, x, 0, 0))

    renderer = SceneRenderer(QGraphicsScene(), MARKER_ICON_PATH)
    renderer.render(data)
    renderer.set_visibility(visibility)

    return renderer


def shown_ids(renderer, scale=ZOOM, center=(0, 0)):
    paint_scene(renderer.scene, center, scale=scale, size=400)

    return renderer.node_label_layer.shown_ids


def test_ids_are_shown_when_switched_on_and_zoomed_in(qapp):
    renderer = render_nodes((1, 0), (2, 40))

    assert shown_ids(renderer, center=(20, 0)) == [1, 2]


def test_ids_are_off_by_default(qapp):
    renderer = render_nodes((1, 0), visibility=Visibility())

    assert shown_ids(renderer) == []


def test_no_ids_when_zoomed_out(qapp):
    renderer = render_nodes((1, 0))

    assert shown_ids(renderer, scale=ZOOM * 0.5) == []


def test_no_ids_while_nodes_are_hidden(qapp):
    renderer = render_nodes((1, 0), visibility=Visibility(nodes=False, node_ids=True))

    assert shown_ids(renderer) == []


def test_label_overlapping_a_lower_id_is_left_out(qapp):
    # The higher id is listed first, but the lower one wins.
    renderer = render_nodes((7, 1), (3, 0), (9, 100))

    assert shown_ids(renderer, center=(50, 0)) == [3, 9]
