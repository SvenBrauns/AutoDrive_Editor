"""Line, Bézier and arc tools with the real window."""

from mouse_helpers import click, drag, press_escape, view_pos
from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest

from autodrive_editor.editing.path_shapes import PathOptions
from autodrive_editor.model.autodrive_data import SUBPRIO_FLAG
from autodrive_editor.model.connections import ConnectionType
from autodrive_editor.settings.app_settings import AppSettings
from autodrive_editor.ui.tools.interaction_mode import InteractionMode

# Test network from conftest: nodes 1, 2, 3 on z=0 at x = 0, 10, 20.


def data(window):
    return window.project_coordinator.autodrive_data


def tool_window(zoomed_window, mode):
    zoomed_window.set_interaction_mode(mode)
    return zoomed_window


def new_nodes(window):
    return [node for node_id, node in sorted(data(window).nodes.items()) if node_id > 3]


def test_line_tool_creates_nodes_with_two_clicks(zoomed_window):
    window = tool_window(zoomed_window, InteractionMode.DRAW_LINE)

    click(window, view_pos(window, 2, 20))
    assert len(data(window)) == 3

    click(window, view_pos(window, 12, 20))

    assert len(new_nodes(window)) == 3
    assert window.actions.undo_action.text() == "Undo: Create line"
    assert window.view.scene().items()


def test_bezier_handle_drag_and_enter_creates_the_curve(zoomed_window):
    window = tool_window(zoomed_window, InteractionMode.DRAW_BEZIER)
    operation = window.create_path_operation

    click(window, view_pos(window, 0, 20))
    click(window, view_pos(window, 20, 20))

    assert operation.is_adjusting
    assert len(data(window)) == 3

    handle = view_pos(window, *operation.handles[0])
    drag(window, handle, handle + QPoint(0, 60))

    assert operation.handles[0][1] > 20 + 5

    QTest.keyClick(window.view, Qt.Key_Return)

    nodes = new_nodes(window)
    assert len(nodes) >= 5
    assert max(node.z for node in nodes) > 22
    assert not operation.is_adjusting


def test_escape_cancels_the_pending_curve(zoomed_window):
    window = tool_window(zoomed_window, InteractionMode.DRAW_ARC)

    click(window, view_pos(window, 0, 20))
    click(window, view_pos(window, 20, 20))
    press_escape(window)

    assert not window.create_path_operation.is_adjusting
    assert len(data(window)) == 3


def test_apply_button_is_enabled_only_while_a_curve_is_pending(zoomed_window):
    window = tool_window(zoomed_window, InteractionMode.DRAW_BEZIER)
    button = window.path_options_widget.apply_button

    assert not button.isEnabled()

    click(window, view_pos(window, 0, 20))
    click(window, view_pos(window, 20, 20))
    assert button.isEnabled()

    button.click()

    assert len(new_nodes(window)) >= 5
    assert not button.isEnabled()


def test_changing_options_updates_the_operation_and_settings(window):
    widget = window.path_options_widget

    widget.spacing_box.setValue(8.0)
    widget.connection_box.setCurrentIndex(widget.connection_box.findData("dual"))
    widget.flag_box.setCurrentIndex(widget.flag_box.findData(SUBPRIO_FLAG))

    expected = PathOptions(8.0, ConnectionType.DUAL, SUBPRIO_FLAG)
    assert window.create_path_operation.options == expected
    assert AppSettings().path_options == expected


def test_tool_panel_has_the_lines_group_with_the_options(window):
    group = window.actions.tool_panel.groups["Lines"]

    assert window.path_options_widget.parent() is not None
    assert group.isAncestorOf(window.path_options_widget)
    assert {
        InteractionMode.DRAW_LINE,
        InteractionMode.DRAW_BEZIER,
        InteractionMode.DRAW_ARC,
    } <= set(window.actions.tool_actions)


def test_loading_data_drops_the_pending_path(zoomed_window, write_xml, qapp):
    window = tool_window(zoomed_window, InteractionMode.DRAW_BEZIER)
    click(window, view_pos(window, 0, 20))
    click(window, view_pos(window, 20, 20))

    window.project_coordinator.load_xml_file(write_xml())
    qapp.processEvents()

    assert window.create_path_operation.start is None
    assert not window.path_options_widget.apply_button.isEnabled()
