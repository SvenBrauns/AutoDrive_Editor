"""A right-click does the same as Esc in every tool except Auswahl."""

import pytest
from mouse_helpers import click, drag, send_mouse, view_pos
from PySide6.QtCore import QEvent, QPoint, QRectF, Qt
from PySide6.QtGui import QPainterPath

from autodrive_editor.measurement.mode import MeasurementMode
from autodrive_editor.model.connections import NO_CONNECTION, read_connection_state
from autodrive_editor.ui.tools.interaction_mode import InteractionMode

# Test network from conftest: nodes 1, 2, 3 on z=0 at x = 0, 10, 20.


def right_click(window, pos):
    click(window, pos, button=Qt.RightButton)


def node_xz(window, node_id):
    node = window.project_coordinator.autodrive_data.get_node(node_id)
    return (node.x, node.z)


def select(window, rect):
    path = QPainterPath()
    path.addRect(rect)
    window.selection_coordinator.handle_area(path, Qt.NoModifier)


def test_right_click_ends_connection_chain_and_keeps_tool(zoomed_window):
    zoomed_window.set_interaction_mode(InteractionMode.CONNECT_REGULAR)
    click(zoomed_window, view_pos(zoomed_window, 0, 0))

    right_click(zoomed_window, view_pos(zoomed_window, 5, 20))
    click(zoomed_window, view_pos(zoomed_window, 20, 0))

    data = zoomed_window.project_coordinator.autodrive_data
    assert read_connection_state(data, 1, 3) == NO_CONNECTION
    assert zoomed_window.connect_nodes_operation.start_node.node_id == 3
    assert zoomed_window.view.interaction_mode == InteractionMode.CONNECT_REGULAR
    assert zoomed_window.view.active_tool.preview_line is not None  # new chain from 3


def test_right_click_during_node_drag_puts_nodes_back(zoomed_window):
    zoomed_window.set_interaction_mode(InteractionMode.MOVE_NODES)
    start = view_pos(zoomed_window, 0, 0)
    drag(zoomed_window, start, start + QPoint(40, 40), release=False)

    send_mouse(
        zoomed_window,
        QEvent.MouseButtonPress,
        start + QPoint(40, 40),
        Qt.RightButton,
        Qt.LeftButton | Qt.RightButton,
    )
    send_mouse(
        zoomed_window,
        QEvent.MouseButtonRelease,
        start + QPoint(40, 40),
        Qt.RightButton,
        Qt.LeftButton,
    )
    send_mouse(
        zoomed_window, QEvent.MouseButtonRelease, start + QPoint(40, 40), Qt.LeftButton, Qt.NoButton
    )

    assert node_xz(zoomed_window, 1) == (0, 0)
    assert zoomed_window.edit_history.undo_stack.count() == 0


def test_right_click_during_rotation_cancels_it(zoomed_window):
    select(zoomed_window, QRectF(-5, -5, 30, 10))
    zoomed_window.set_interaction_mode(InteractionMode.ROTATE_SELECTION)
    center, radius = zoomed_window.view.active_tool.ring
    grab = view_pos(zoomed_window, center.x() + radius, center.y())
    end = view_pos(zoomed_window, center.x(), center.y() + radius)
    drag(zoomed_window, grab, end, release=False)

    send_mouse(
        zoomed_window, QEvent.MouseButtonPress, end, Qt.RightButton, Qt.LeftButton | Qt.RightButton
    )
    send_mouse(zoomed_window, QEvent.MouseButtonRelease, end, Qt.LeftButton, Qt.NoButton)

    assert node_xz(zoomed_window, 1) == pytest.approx((0, 0))
    assert zoomed_window.edit_history.undo_stack.count() == 0


def test_right_click_clears_then_ends_measurement(zoomed_window):
    zoomed_window.set_measurement_mode(MeasurementMode.DISTANCE)
    click(zoomed_window, view_pos(zoomed_window, 5, 20))

    right_click(zoomed_window, view_pos(zoomed_window, 5, 20))
    assert not zoomed_window.measurement_controller.state.has_start_point
    assert zoomed_window.view.measurement_active

    right_click(zoomed_window, view_pos(zoomed_window, 5, 20))
    assert not zoomed_window.view.measurement_active


@pytest.mark.parametrize(
    "mode",
    [
        InteractionMode.CREATE_NODES,
        InteractionMode.DELETE_NODES,
        InteractionMode.TOGGLE_NODE_TYPE,
    ],
)
def test_right_click_on_a_node_changes_nothing(zoomed_window, mode):
    zoomed_window.set_interaction_mode(mode)

    right_click(zoomed_window, view_pos(zoomed_window, 10, 0))

    assert zoomed_window.edit_history.undo_stack.count() == 0
    assert zoomed_window.view.interaction_mode == mode


def test_selection_tool_still_box_selects_with_right_drag(zoomed_window):
    zoomed_window.set_interaction_mode(InteractionMode.SELECT)

    drag(
        zoomed_window,
        view_pos(zoomed_window, -5, -5),
        view_pos(zoomed_window, 15, 5),
        button=Qt.RightButton,
    )

    assert zoomed_window.node_selection.selected_node_ids == {1, 2}
