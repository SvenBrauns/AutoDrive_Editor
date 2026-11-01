import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QToolButton

from autodrive_editor.measurement.mode import MeasurementMode
from autodrive_editor.ui.actions.tool_catalog import (
    CONNECT_TOOL,
    CREATE_TOOL,
    DRAW_TOOL,
    MARKER_TOOL,
    MEASURE_TOOL,
)
from autodrive_editor.ui.tools.interaction_mode import InteractionMode


def tool_button(window, text):
    for action, button in window.actions.tool_panel.tool_buttons.items():
        if action.text() == text:
            return button
    raise AssertionError(f"no tool button {text!r}")


def checked_tools(window):
    return {mode for mode, action in window.actions.tool_actions.items() if action.isChecked()}


def test_panel_shows_node_group_with_move_tool(window):
    panel = window.actions.tool_panel

    assert window.dockWidgetArea(panel) == Qt.LeftDockWidgetArea
    assert tool_button(window, "Move").isVisible()


def test_clicking_move_tool_activates_it(window):
    tool_button(window, "Move").click()

    assert window.view.interaction_mode == InteractionMode.MOVE_NODES
    assert checked_tools(window) == {InteractionMode.MOVE_NODES}
    assert window.status.text().startswith("Mode: Move nodes – ")


def test_exactly_one_tool_is_checked(window):
    tool_button(window, "Move").click()
    window.actions.selection_action.trigger()

    assert window.view.interaction_mode == InteractionMode.SELECT
    assert checked_tools(window) == {InteractionMode.SELECT}


def test_measure_is_a_tool_and_another_tool_ends_measuring(window):
    tool_button(window, "Move").click()

    tool_button(window, "Measure").click()
    assert window.view.interaction_mode == InteractionMode.MEASURE_DISTANCE
    assert window.measurement_coordinator.mode == MeasurementMode.DISTANCE
    assert checked_tools(window) == {InteractionMode.MEASURE_DISTANCE}

    tool_button(window, "Move").click()
    assert window.view.interaction_mode != InteractionMode.MEASURE_DISTANCE
    assert window.measurement_coordinator.mode == MeasurementMode.INACTIVE
    assert checked_tools(window) == {InteractionMode.MOVE_NODES}


def test_panel_can_be_toggled_from_view_menu(window, qapp):
    toggle = window.actions.tool_panel.toggleViewAction()

    toggle.trigger()
    qapp.processEvents()
    assert not window.actions.tool_panel.isVisible()

    toggle.trigger()
    qapp.processEvents()
    assert window.actions.tool_panel.isVisible()


def test_debug_dock_shows_move_tool_name(window, qapp):
    window.debug_dock.show()
    tool_button(window, "Move").click()
    qapp.processEvents()

    assert window.debug_dock.interaction_mode_value.text() == "Move nodes"


def test_tool_buttons_follow_mode_changes_from_code(window):
    window.set_interaction_mode(InteractionMode.CONNECT_DUAL)

    assert checked_tools(window) == {InteractionMode.CONNECT_DUAL}


# --- layout: icons, groups, labels, shortcuts --------------


def nodes_group(window):
    return window.actions.tool_panel.groups["Nodes"]


def test_tool_buttons_show_icons_only_by_default(window):
    for action, button in window.actions.tool_panel.tool_buttons.items():
        assert not action.icon().isNull(), action.text()
        assert button.toolButtonStyle() == Qt.ToolButtonIconOnly


def test_tooltips_name_tool_and_shortcut(window):
    tooltip = window.actions.tool_actions[InteractionMode.MOVE_NODES].toolTip()

    assert "<b>Move</b> (V)" in tooltip
    assert "left-dragging" in tooltip


def test_labels_can_be_shown(window):
    window.actions.tool_labels_action.trigger()

    for button in window.actions.tool_panel.tool_buttons.values():
        assert button.toolButtonStyle() == Qt.ToolButtonTextBesideIcon

    window.actions.tool_labels_action.trigger()
    assert all(
        button.toolButtonStyle() == Qt.ToolButtonIconOnly
        for button in window.actions.tool_panel.tool_buttons.values()
    )


def test_group_can_be_collapsed(window, qapp):
    group = nodes_group(window)
    button = window.actions.tool_panel.tool_buttons[
        window.actions.tool_actions[InteractionMode.MOVE_NODES]
    ]

    group.header_button.click()
    qapp.processEvents()
    assert not group.is_expanded
    assert not button.isVisible()

    group.header_button.click()
    qapp.processEvents()
    assert button.isVisible()


@pytest.mark.parametrize(
    ("keys", "mode"),
    [
        ("V", InteractionMode.MOVE_NODES),
        ("R", InteractionMode.ROTATE_SELECTION),
        ("L", InteractionMode.DELETE_NODES),
        ("E", InteractionMode.CREATE_NODES),
        ("T", InteractionMode.TOGGLE_NODE_TYPE),
        ("1", InteractionMode.CONNECT_REGULAR),
        ("2", InteractionMode.CONNECT_DUAL),
        ("3", InteractionMode.CONNECT_REVERSE),
        ("A", InteractionMode.SELECT),
    ],
)
def test_keyboard_shortcuts_pick_tools(window, qapp, keys, mode):
    window.activateWindow()
    window.view.setFocus()
    qapp.processEvents()

    QTest.keyClick(window.view, keys)
    qapp.processEvents()

    assert window.view.interaction_mode == mode
    assert checked_tools(window) == {mode}


def test_shift_e_picks_subprio_create_tool(window, qapp):
    window.activateWindow()
    window.view.setFocus()

    QTest.keyClick(window.view, Qt.Key_E, Qt.ShiftModifier)
    qapp.processEvents()

    assert window.view.interaction_mode == InteractionMode.CREATE_SUBPRIO_NODES


def test_shortcuts_work_with_hidden_panel(window, qapp):
    window.actions.tool_panel.hide()
    window.activateWindow()
    window.view.setFocus()

    QTest.keyClick(window.view, "V")
    qapp.processEvents()

    assert window.view.interaction_mode == InteractionMode.MOVE_NODES


def test_undo_and_redo_are_icon_buttons_in_top_toolbar(window):
    buttons = [
        widget
        for widget in window.actions.quick_access_toolbar.findChildren(QToolButton)
        if widget.defaultAction() in (window.actions.undo_action, window.actions.redo_action)
    ]

    assert len(buttons) == 2
    assert all(button.toolButtonStyle() == Qt.ToolButtonIconOnly for button in buttons)
    assert all(not button.icon().isNull() for button in buttons)


@pytest.mark.parametrize("mode", [m for m in InteractionMode if m != InteractionMode.NAVIGATE])
def test_every_tool_explains_itself_in_the_status_bar(window, mode):
    window.set_interaction_mode(mode)

    text = window.status.text()
    assert text.startswith(f"Mode: {mode.display_name} – ")
    assert len(text) > len(f"Mode: {mode.display_name} – ") + 10


# --- merged tools: one strip button, variants in the options bar ----


def strip_action(window, tool):
    return window.actions.merged_tool_actions[tool]


def test_merged_tool_button_shows_the_current_variant(window):
    create = strip_action(window, CREATE_TOOL)

    assert "<b>Create – Regular</b> (E)" in create.toolTip()

    window.set_interaction_mode(InteractionMode.CREATE_SUBPRIO_NODES)
    subprio = window.actions.tool_actions[InteractionMode.CREATE_SUBPRIO_NODES]

    assert create.isChecked()
    assert create.icon().cacheKey() == subprio.icon().cacheKey()
    assert "<b>Create – Subprio</b> (Shift+E)" in create.toolTip()


def test_merged_tool_button_activates_the_last_variant(window):
    window.set_interaction_mode(InteractionMode.CONNECT_DUAL)
    window.set_interaction_mode(InteractionMode.MOVE_NODES)

    assert not strip_action(window, CONNECT_TOOL).isChecked()

    tool_button(window, "Connect").click()

    assert window.view.interaction_mode == InteractionMode.CONNECT_DUAL
    assert strip_action(window, CONNECT_TOOL).isChecked()


def test_clicking_the_active_merged_tool_keeps_it_checked(window):
    tool_button(window, "Draw").click()
    tool_button(window, "Draw").click()

    assert window.view.interaction_mode == InteractionMode.DRAW_LINE
    assert strip_action(window, DRAW_TOOL).isChecked()


def test_switching_the_measure_variant_changes_the_measurement(window):
    window.set_interaction_mode(InteractionMode.MEASURE_DISTANCE)
    window.actions.tool_actions[InteractionMode.MEASURE_ANGLE].trigger()

    assert window.measurement_coordinator.mode == MeasurementMode.ANGLE
    assert strip_action(window, MEASURE_TOOL).isChecked()
    assert window.options_bar.stack.currentWidget().defaultAction() is (
        window.actions.align_measurement_action
    )


@pytest.mark.parametrize(
    ("key", "modifiers", "tool", "mode"),
    [
        (Qt.Key_E, Qt.NoModifier, CREATE_TOOL, InteractionMode.CREATE_NODES),
        (Qt.Key_E, Qt.ShiftModifier, CREATE_TOOL, InteractionMode.CREATE_SUBPRIO_NODES),
        (Qt.Key_3, Qt.NoModifier, CONNECT_TOOL, InteractionMode.CONNECT_REVERSE),
        (Qt.Key_I, Qt.NoModifier, DRAW_TOOL, InteractionMode.DRAW_LINE),
        (Qt.Key_K, Qt.NoModifier, DRAW_TOOL, InteractionMode.DRAW_ARC),
        (Qt.Key_B, Qt.NoModifier, DRAW_TOOL, InteractionMode.DRAW_BEZIER),
        (Qt.Key_M, Qt.NoModifier, MARKER_TOOL, InteractionMode.ADD_MARKER),
        (Qt.Key_M, Qt.ShiftModifier, MARKER_TOOL, InteractionMode.EDIT_MARKER),
        (Qt.Key_M, Qt.ControlModifier, MARKER_TOOL, InteractionMode.MOVE_MARKER),
        (
            Qt.Key_M,
            Qt.ControlModifier | Qt.ShiftModifier,
            MARKER_TOOL,
            InteractionMode.DELETE_MARKER,
        ),
        (Qt.Key_D, Qt.NoModifier, MEASURE_TOOL, InteractionMode.MEASURE_DISTANCE),
        (Qt.Key_D, Qt.ShiftModifier, MEASURE_TOOL, InteractionMode.MEASURE_ANGLE),
    ],
)
def test_variant_keys_pick_tool_and_variant(window, qapp, key, modifiers, tool, mode):
    window.activateWindow()
    window.view.setFocus()

    QTest.keyClick(window.view, key, modifiers)
    qapp.processEvents()

    assert window.view.interaction_mode == mode
    assert strip_action(window, tool).isChecked()
    assert window.actions.current_variants[tool] == mode
