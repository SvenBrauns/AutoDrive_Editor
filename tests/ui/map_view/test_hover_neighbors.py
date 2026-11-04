"""Hovering a node highlights its neighbours, in every tool."""

import pytest
from drawing_helpers import RED, drawn_color
from mouse_helpers import hover, view_pos
from PySide6.QtGui import QColor

from autodrive_editor.rendering.display_style import DisplayStyle
from autodrive_editor.ui.tools.interaction_mode import InteractionMode

# Test network from conftest: 1 -> 2 -> 3 on the line z=0 at x = 0, 10, 20.

PURPLE = QColor(*DisplayStyle().neighbor_node_color).name()


@pytest.mark.parametrize("mode", [InteractionMode.SELECT, InteractionMode.DELETE_NODES])
def test_hovering_a_node_highlights_its_neighbors(zoomed_window, mode):
    zoomed_window.set_interaction_mode(mode)

    hover(zoomed_window, view_pos(zoomed_window, 10, 0))

    assert drawn_color(zoomed_window, 0, 0) == PURPLE
    assert drawn_color(zoomed_window, 20, 0) == PURPLE
    assert drawn_color(zoomed_window, 10, 0) == RED

    hover(zoomed_window, view_pos(zoomed_window, 5, 30))

    assert drawn_color(zoomed_window, 0, 0) == RED
