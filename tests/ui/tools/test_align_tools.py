"""Aligning selected nodes to a reference node."""

import pytest
from mouse_helpers import click, view_pos

from autodrive_editor.ui.tools.interaction_mode import InteractionMode


@pytest.fixture
def align_window(window, write_xml, qapp):
    """Reference node 1 at (0, 0), height 5; nodes 2 (10, 4) and 3 (20, -6)."""

    path = write_xml(x="0;10;20", y="5;1;2", z="0;4;-6", out="2;3;", incoming=";1;2", flags="0;0;0")
    window.project_coordinator.load_xml_file(path)
    window.view.set_zoom_level(4.0)
    window.view.centerOn(10, 0)
    qapp.processEvents()
    window.data = window.project_coordinator.autodrive_data
    window.node_selection.replace({2, 3})
    return window


def node(window, node_id):
    n = window.data.nodes[node_id]
    return round(n.x, 6), round(n.y, 6), round(n.z, 6)


def use(window, mode, reference=(0, 0)):
    window.set_interaction_mode(mode)
    click(window, view_pos(window, *reference))


def test_horizontal_puts_selection_on_the_reference_line(align_window):
    use(align_window, InteractionMode.ALIGN_HORIZONTAL)

    assert node(align_window, 2)[0::2] == (10, 0)
    assert node(align_window, 3)[0::2] == (20, 0)
    assert node(align_window, 1) == (0, 5, 0)


def test_vertical_puts_selection_on_the_reference_line(align_window):
    use(align_window, InteractionMode.ALIGN_VERTICAL)

    assert node(align_window, 2)[0::2] == (0, 4)
    assert node(align_window, 3)[0::2] == (0, -6)


def test_horizontal_follows_the_rotated_view(align_window):
    align_window.view.set_exact_rotation_angle(90)

    use(align_window, InteractionMode.ALIGN_HORIZONTAL)

    # Rotated by 90°, a screen-horizontal line runs along the map's z axis.
    assert node(align_window, 2)[0::2] == (0, 4)
    assert node(align_window, 3)[0::2] == (0, -6)


def test_horizontal_follows_a_diagonal_view(align_window):
    align_window.view.set_exact_rotation_angle(45)

    use(align_window, InteractionMode.ALIGN_HORIZONTAL)

    # At 45° the screen-horizontal line through (0, 0) is x = -z.
    x, _, z = node(align_window, 2)
    assert x == pytest.approx(-z)
    assert (x, z) == pytest.approx((3, -3))


def test_height_like_reference(align_window):
    use(align_window, InteractionMode.ALIGN_HEIGHT)

    assert node(align_window, 2) == (10, 5, 4)
    assert node(align_window, 3) == (20, 5, -6)


def test_each_align_is_one_undo_step(align_window):
    use(align_window, InteractionMode.ALIGN_HORIZONTAL)

    align_window.edit_history.undo()

    assert node(align_window, 2) == (10, 1, 4)
    assert node(align_window, 3) == (20, 2, -6)


def test_reference_inside_the_selection_stays(align_window):
    align_window.node_selection.replace({1, 2, 3})

    use(align_window, InteractionMode.ALIGN_HORIZONTAL, reference=(10, 4))

    assert node(align_window, 2) == (10, 1, 4)
    assert node(align_window, 1)[0::2] == (0, 4)


def test_without_selection_the_status_explains(align_window):
    align_window.node_selection.clear()

    use(align_window, InteractionMode.ALIGN_HORIZONTAL)

    assert "select" in align_window.status.text()
    assert not align_window.edit_history.can_undo


def test_height_from_terrain_needs_a_heightmap(align_window):
    use(align_window, InteractionMode.HEIGHT_FROM_TERRAIN)

    assert align_window.status.text() == "No heightmap loaded"


def test_height_from_terrain_sets_each_node_to_the_ground(align_window, sloped_heightmap):
    align_window.heightmap.load(sloped_heightmap)

    use(align_window, InteractionMode.HEIGHT_FROM_TERRAIN)

    for node_id in (2, 3):
        n = align_window.data.nodes[node_id]
        assert n.y == pytest.approx(align_window._get_terrain_height(n.x, n.z))
    assert node(align_window, 1) == (0, 5, 0)


def test_aligned_nodes_follow_the_terrain(align_window, sloped_heightmap):
    align_window.heightmap.load(sloped_heightmap)
    terrain = align_window._get_terrain_height
    offset = 1 - terrain(10, 4)  # node 2's height above the terrain before aligning

    use(align_window, InteractionMode.ALIGN_HORIZONTAL)

    assert align_window.data.nodes[2].y == pytest.approx(terrain(10, 0) + offset)
