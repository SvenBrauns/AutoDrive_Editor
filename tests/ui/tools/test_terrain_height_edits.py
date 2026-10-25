"""Moving and rotating nodes lets them follow the heightmap."""

import pytest
from mouse_helpers import drag, view_pos
from PySide6.QtCore import QPoint, QRectF, Qt
from PySide6.QtGui import QPainterPath

from autodrive_editor.ui.tools.interaction_mode import InteractionMode


@pytest.fixture
def terrain_window(zoomed_window, sloped_heightmap):
    zoomed_window.heightmap.load(sloped_heightmap)
    return zoomed_window


def node(window, node_id):
    return window.project_coordinator.autodrive_data.get_node(node_id)


def terrain(window, x, z):
    return window._get_terrain_height(x, z)


def select_all(window):
    path = QPainterPath()
    path.addRect(QRectF(-5, -5, 30, 10))
    window.selection_coordinator.handle_area(path, Qt.NoModifier)


def test_heightmap_slope_is_visible_in_test_setup(terrain_window):
    assert terrain(terrain_window, 200, 0) > terrain(terrain_window, -200, 0)


def test_moved_node_follows_the_terrain(terrain_window):
    terrain_window.set_interaction_mode(InteractionMode.MOVE_NODES)
    start = view_pos(terrain_window, 0, 0)

    drag(terrain_window, start, start + QPoint(200, 0))

    moved = node(terrain_window, 1)
    expected = terrain(terrain_window, moved.x, moved.z) - terrain(terrain_window, 0, 0) + 0.0
    assert moved.x > 40
    assert moved.y == pytest.approx(expected)
    assert moved.y != 0


def test_node_above_terrain_keeps_its_distance_when_moved(terrain_window):
    lifted = node(terrain_window, 1)
    lifted.y = terrain(terrain_window, 0, 0) + 8.0  # like a bridge
    terrain_window.set_interaction_mode(InteractionMode.MOVE_NODES)
    start = view_pos(terrain_window, 0, 0)

    drag(terrain_window, start, start + QPoint(200, 0))

    assert lifted.y - terrain(terrain_window, lifted.x, lifted.z) == pytest.approx(8.0)


def test_undo_restores_the_old_height(terrain_window):
    terrain_window.set_interaction_mode(InteractionMode.MOVE_NODES)
    start = view_pos(terrain_window, 0, 0)
    drag(terrain_window, start, start + QPoint(200, 0))

    terrain_window.actions.undo_action.trigger()

    assert node(terrain_window, 1).y == 0


def test_rotated_nodes_follow_the_terrain(terrain_window):
    select_all(terrain_window)  # center (10, 0), ring radius 16 at zoom 4
    terrain_window.set_interaction_mode(InteractionMode.ROTATE_SELECTION)

    drag(terrain_window, view_pos(terrain_window, 26, 0), view_pos(terrain_window, 10, 16), steps=8)

    for node_id, start_x in ((1, 0), (3, 20)):
        rotated = node(terrain_window, node_id)
        expected = terrain(terrain_window, rotated.x, rotated.z) - terrain(
            terrain_window, start_x, 0
        )
        assert rotated.y == pytest.approx(expected)


def test_without_heightmap_the_height_stays(zoomed_window):
    zoomed_window.set_interaction_mode(InteractionMode.MOVE_NODES)
    start = view_pos(zoomed_window, 0, 0)

    drag(zoomed_window, start, start + QPoint(200, 0))

    assert node(zoomed_window, 1).y == 0
