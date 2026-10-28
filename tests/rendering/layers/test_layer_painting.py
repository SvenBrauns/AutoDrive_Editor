"""The layers painted into an image at different zoom levels."""

import pytest
from drawing_helpers import paint_scene
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QGraphicsScene

from autodrive_editor.model.autodrive_data import SUBPRIO_FLAG, AutoDriveData, MarkerData, NodeData
from autodrive_editor.paths import MARKER_ICON_PATH
from autodrive_editor.rendering.display_style import DisplayStyle
from autodrive_editor.rendering.scene_renderer import SceneRenderer
from autodrive_editor.rendering.visibility import Visibility


def render(*nodes, markers=()):
    data = AutoDriveData()

    for node in nodes:
        data.add_node(node)

    for marker in markers:
        data.add_marker(marker)

    renderer = SceneRenderer(QGraphicsScene(), MARKER_ICON_PATH)
    renderer.render(data)

    return renderer


@pytest.fixture
def long_connection(qapp):
    return render(NodeData(1, 0, 0, 0, outgoing={2}), NodeData(2, 100, 0, 0, incoming={1}))


def test_arrow_appears_once_the_connection_is_long_enough_on_screen(long_connection):
    paint_scene(long_connection.scene, (50, 0), scale=0.1)
    assert long_connection.connection_layer.drawn_arrows == 0

    paint_scene(long_connection.scene, (50, 0), scale=2.0)
    assert long_connection.connection_layer.drawn_arrows == 1


def test_arrow_sits_in_the_middle_of_the_connection(long_connection):
    color = QColor(*DisplayStyle().regular_connection_color).name()

    painted = paint_scene(long_connection.scene, (50, 0), scale=4.0)

    # The thin line alone only partly covers the pixel next to it; the arrow covers it fully.
    assert painted.color_at(49, 0.25) == color
    assert painted.color_at(20, 0.25) != color


def test_line_is_drawn_at_every_zoom_level(long_connection):
    for scale in (0.05, 1.0, 20.0):
        painted = paint_scene(long_connection.scene, (30, 0), scale=scale)
        pixel = QColor(painted.color_at(30, 0))

        # Thin lines are antialiased, so only the hue is compared.
        assert pixel.green() > pixel.red() + 60, scale


def test_names_that_would_overlap_are_left_out(qapp):
    renderer = render(
        NodeData(1, 0, 0, 0),
        NodeData(2, 2, 0, 0),
        NodeData(3, 200, 0, 0),
        markers=[MarkerData(1, "Hof"), MarkerData(2, "Silo"), MarkerData(3, "Feld")],
    )

    paint_scene(renderer.scene, (100, 0), scale=1.0, size=400)

    assert renderer.marker_layer.shown_names == {1: "Hof", 3: "Feld"}


def test_names_can_be_hidden(qapp):
    renderer = render(NodeData(1, 0, 0, 0), markers=[MarkerData(1, "Hof")])
    renderer.set_marker_names_visible(False)

    paint_scene(renderer.scene, (0, 0), scale=1.0)

    assert renderer.marker_layer.shown_names == {}
    assert renderer.marker_layer.drawn_markers == 1


def test_markers_are_drawn_without_names_when_zoomed_out(qapp):
    renderer = render(NodeData(1, 0, 0, 0), markers=[MarkerData(1, "Hof")])

    paint_scene(renderer.scene, (0, 0), scale=0.02)

    assert renderer.marker_layer.drawn_markers == 1
    assert renderer.marker_layer.shown_names == {}


@pytest.mark.parametrize(("scale", "shown"), [(0.6, False), (0.8, True), (1.0, True)])
def test_names_fade_in_below_their_zoom(qapp, scale, shown):
    renderer = render(NodeData(1, 0, 0, 0), markers=[MarkerData(1, "Hof")])

    paint_scene(renderer.scene, (0, 0), scale=scale)

    assert (renderer.marker_layer.shown_names == {1: "Hof"}) == shown


def test_hidden_connection_kind_is_not_drawn_with_its_arrow(long_connection):
    long_connection.set_visibility(Visibility(regular_connections=False))

    painted = paint_scene(long_connection.scene, (50, 0), scale=2.0)

    assert long_connection.connection_layer.drawn_arrows == 0
    assert painted.color_at(30, 0) == "#ffffff"


def test_other_connection_kinds_are_still_drawn(long_connection):
    long_connection.set_visibility(Visibility(dual_connections=False))

    paint_scene(long_connection.scene, (50, 0), scale=2.0)

    assert long_connection.connection_layer.drawn_arrows == 1


def test_connection_into_subprio_node_keeps_its_type_color(qapp):
    renderer = render(
        NodeData(1, 0, 0, 0, outgoing={2}), NodeData(2, 100, 0, 0, flag=SUBPRIO_FLAG, incoming={1})
    )
    color = QColor(*DisplayStyle().regular_connection_color).name()

    assert paint_scene(renderer.scene, (50, 0), scale=4.0).color_at(49, 0.25) == color


def test_dual_connection_gets_an_arrow_a_third_from_each_end(qapp):
    renderer = render(
        NodeData(1, 0, 0, 0, outgoing={2}, incoming={2}),
        NodeData(2, 90, 0, 0, outgoing={1}, incoming={1}),
    )
    color = QColor(*DisplayStyle().dual_connection_color).name()

    painted = paint_scene(renderer.scene, (45, 0), scale=4.0)

    assert renderer.connection_layer.drawn_arrows == 2
    # Each arrow's wide base faces the middle, its tip points to the nearer end.
    assert painted.color_at(31, 0.5) == color
    assert painted.color_at(59, 0.5) == color
    assert painted.color_at(45, 0.5) != color


def test_short_dual_connection_has_no_arrows(qapp):
    renderer = render(
        NodeData(1, 0, 0, 0, outgoing={2}, incoming={2}),
        NodeData(2, 90, 0, 0, outgoing={1}, incoming={1}),
    )

    paint_scene(renderer.scene, (45, 0), scale=0.05)

    assert renderer.connection_layer.drawn_arrows == 0


def test_node_colors_come_from_the_display_style(qapp):
    renderer = render(NodeData(1, 0, 0, 0), NodeData(2, 10, 0, 0, flag=SUBPRIO_FLAG))
    renderer.set_display_style(
        DisplayStyle(regular_node_color=(0, 0, 255), subprio_node_color=(255, 0, 255))
    )

    painted = paint_scene(renderer.scene, (5, 0), scale=8.0)

    assert (painted.color_at(0, 0), painted.color_at(10, 0)) == ("#0000ff", "#ff00ff")


def test_hidden_nodes_and_their_selection_are_not_drawn(qapp):
    renderer = render(NodeData(1, 0, 0, 0))
    renderer.set_selected_node_ids({1})
    renderer.set_visibility(Visibility(nodes=False))

    assert paint_scene(renderer.scene, (0, 0), scale=4.0).color_at(0, 0) == "#ffffff"

    renderer.set_visibility(Visibility())

    assert paint_scene(renderer.scene, (0, 0), scale=4.0).color_at(0, 0) != "#ffffff"


def test_markers_can_be_hidden(qapp):
    renderer = render(NodeData(1, 0, 0, 0), markers=[MarkerData(1, "Hof")])
    renderer.set_visibility(Visibility(markers=False))

    paint_scene(renderer.scene, (0, 0), scale=1.0)

    assert renderer.marker_layer.drawn_markers == 0
    assert renderer.marker_layer.shown_names == {}


@pytest.mark.parametrize(("parking", "expected"), [(True, 1), (False, 0)])
def test_parking_sign_is_drawn_on_parking_markers_only(qapp, parking, expected):
    markers = [MarkerData(1, "Hof"), MarkerData(2, "Silo")]
    renderer = render(NodeData(1, 0, 0, 0), NodeData(2, 50, 0, 0), markers=markers)
    renderer.set_parking_markers([markers[0]])
    renderer.set_visibility(Visibility(parking=parking))

    paint_scene(renderer.scene, (25, 0), scale=2.0)

    assert renderer.marker_layer.drawn_markers == 2
    assert renderer.marker_layer.drawn_parking == expected
