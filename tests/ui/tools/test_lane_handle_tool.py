"""Dragging the handles of station lanes while the dialog is open beside the map."""

import pytest
from mouse_helpers import click, drag, press_escape, view_pos
from PySide6.QtCore import Qt

from autodrive_editor.ui.tools.lane_handle_tool import LaneHandleTool

HANDLE = (3, "end", 10, 10)


@pytest.fixture
def drags(zoomed_window):
    window = zoomed_window
    dragged = []
    # One handle of row 3 at (10, 10); node 7 is under the mouse everywhere.
    tool = LaneHandleTool(
        window.view, lambda: [HANDLE], lambda *args: dragged.append(args), lambda _: 7
    )
    window.view.set_override_tool(tool)
    yield window, dragged
    window.view.set_override_tool(None)


def test_dragging_a_handle_passes_the_map_position_and_the_node_on(drags):
    window, dragged = drags

    drag(window, view_pos(window, 10, 10), view_pos(window, 0, 20))

    handle, x, z, node_id, snap = dragged[-1]
    assert (handle, node_id, snap) == (HANDLE, 7, False)
    assert (x, z) == pytest.approx((0, 20), abs=0.5)


def test_shift_is_passed_on_for_snapping(drags):
    window, dragged = drags

    drag(window, view_pos(window, 10, 10), view_pos(window, 1, 20), modifiers=Qt.ShiftModifier)

    assert dragged[-1][4] is True


def test_dragging_beside_the_handles_drags_nothing(drags):
    window, dragged = drags

    drag(window, view_pos(window, 20, 20), view_pos(window, 25, 20))

    assert not dragged


class Drawing:
    def __init__(self):
        self.calls = []

    def click(self, handle, x, z, node_id):
        self.calls.append(("click", handle, round(x), round(z), node_id))
        return True

    def remove_last(self):
        self.calls.append(("remove_last",))
        return True

    def finish(self):
        self.calls.append(("finish",))
        return True


def test_clicks_right_clicks_and_esc_go_to_the_drawing(zoomed_window):
    window, drawing, dragged = zoomed_window, Drawing(), []
    tool = LaneHandleTool(
        window.view, lambda: [HANDLE], lambda *args: dragged.append(args), lambda _: 7, drawing
    )
    window.view.set_override_tool(tool)

    try:
        click(window, view_pos(window, 30, 20))
        click(window, view_pos(window, 10, 10))
        click(window, view_pos(window, 30, 20), button=Qt.RightButton)
        press_escape(window)
        # Dragging a handle or the map is no click.
        drag(window, view_pos(window, 10, 10), view_pos(window, 0, 20))
        drag(window, view_pos(window, 30, 20), view_pos(window, 40, 20))
        calls = list(drawing.calls)
    finally:
        window.view.set_override_tool(None)

    assert calls == [
        ("click", None, 30, 20, 7),
        ("click", HANDLE, 10, 10, 7),
        ("remove_last",),
        ("finish",),
    ]
    assert len(dragged) == 5
