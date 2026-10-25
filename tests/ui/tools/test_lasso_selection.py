"""Freehand lasso selection with Shift + right drag."""

import pytest
from mouse_helpers import click, press_escape, send_mouse, view_pos
from PySide6.QtCore import QEvent, Qt
from PySide6.QtWidgets import QGraphicsPathItem

from autodrive_editor.ui.map_view.area_selection import AreaSelectionController
from autodrive_editor.ui.tools.interaction_mode import InteractionMode

# U shape around node 1 (x=0) and node 3 (x=20), leaving out node 2 (x=10).
U_SHAPE = [(-5, -5), (5, -5), (5, 3), (15, 3), (15, -5), (25, -5), (25, 5), (-5, 5)]

SHIFT = Qt.ShiftModifier


@pytest.fixture
def select_mode(zoomed_window):
    zoomed_window.set_interaction_mode(InteractionMode.SELECT)
    return zoomed_window


def selected(window):
    return window.node_selection.selected_node_ids


def lasso_items(window):
    return [
        item
        for item in window.scene.items()
        if isinstance(item, QGraphicsPathItem)
        and item.zValue() == AreaSelectionController.LASSO_Z_VALUE
    ]


def draw_lasso(window, points, modifiers=SHIFT, release=True):
    """Presses the right button at the first point and moves through the
    others in small steps."""

    positions = [view_pos(window, x, z) for x, z in points]
    send_mouse(
        window, QEvent.MouseButtonPress, positions[0], Qt.RightButton, Qt.RightButton, modifiers
    )

    for start, end in zip(positions, positions[1:] + positions[:1], strict=True):
        for step in range(1, 6):
            position = start + (end - start) * step / 5
            send_mouse(window, QEvent.MouseMove, position, Qt.NoButton, Qt.RightButton, modifiers)

    if release:
        send_mouse(
            window, QEvent.MouseButtonRelease, positions[0], Qt.RightButton, Qt.NoButton, modifiers
        )


def test_lasso_selects_nodes_inside_the_freehand_shape(select_mode):
    draw_lasso(select_mode, U_SHAPE)

    assert selected(select_mode) == {1, 3}


def test_lasso_line_is_shown_while_drawing_and_removed_afterwards(select_mode):
    draw_lasso(select_mode, U_SHAPE, release=False)
    assert len(lasso_items(select_mode)) == 1
    assert select_mode.scene_renderer.selected_node_ids == {1, 3}  # highlighted preview

    send_mouse(
        select_mode,
        QEvent.MouseButtonRelease,
        view_pos(select_mode, -5, -5),
        Qt.RightButton,
        Qt.NoButton,
        SHIFT,
    )

    assert lasso_items(select_mode) == []


def test_escape_cancels_the_lasso(select_mode):
    click(select_mode, view_pos(select_mode, 10, 0))
    draw_lasso(select_mode, U_SHAPE, release=False)

    press_escape(select_mode)

    assert lasso_items(select_mode) == []
    assert selected(select_mode) == {2}


def test_ctrl_adds_the_lasso_to_the_selection(select_mode):
    click(select_mode, view_pos(select_mode, 10, 0))

    draw_lasso(select_mode, U_SHAPE, modifiers=SHIFT | Qt.ControlModifier)

    assert selected(select_mode) == {1, 2, 3}


def test_lasso_works_in_a_rotated_view(select_mode):
    select_mode.view.set_exact_rotation_angle(90)

    draw_lasso(select_mode, U_SHAPE)

    assert selected(select_mode) == {1, 3}
