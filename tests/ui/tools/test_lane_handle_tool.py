"""Turning station lanes by dragging their handles while the dialog is open beside the map."""

import pytest
from mouse_helpers import drag, view_pos
from PySide6.QtCore import Qt

from autodrive_editor.ui.tools.lane_handle_tool import LaneHandleTool


@pytest.fixture
def turns(zoomed_window):
    window = zoomed_window
    turned = []
    # Lane of row 3 with its stop at (0, 10) and its handle 10 m to the right.
    tool = LaneHandleTool(
        window.view,
        lambda: [(3, 10, 10, 0, 10)],
        lambda row, heading: turned.append((row, heading)),
    )
    window.view.set_override_tool(tool)
    yield window, turned
    window.view.set_override_tool(None)


def test_dragging_a_handle_turns_its_lane_around_the_stop(turns):
    window, turned = turns

    drag(window, view_pos(window, 10, 10), view_pos(window, 0, 20))

    # Straight down the map from the stop.
    assert turned[-1] == (3, pytest.approx(180, abs=1))


def test_shift_snaps_to_15_degrees(turns):
    window, turned = turns

    drag(window, view_pos(window, 10, 10), view_pos(window, 1, 20), modifiers=Qt.ShiftModifier)

    assert turned[-1] == (3, 180)


def test_dragging_beside_the_handles_turns_nothing(turns):
    window, turned = turns

    drag(window, view_pos(window, 20, 20), view_pos(window, 25, 20))

    assert not turned
