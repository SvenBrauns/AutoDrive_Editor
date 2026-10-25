from PySide6.QtCore import QEvent, QPoint, Qt

from measurement.measurement_mode import MeasurementMode
from ui.interaction_mode import InteractionMode


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
    assert tool_button(window, "Verschieben").isVisible()


def test_clicking_move_tool_activates_it(window):
    tool_button(window, "Verschieben").click()

    assert window.view.interaction_mode == InteractionMode.MOVE_NODES
    assert checked_tools(window) == {InteractionMode.MOVE_NODES}
    assert window.status.text() == "Modus: Nodes verschieben"


def test_exactly_one_tool_is_checked(window):
    tool_button(window, "Verschieben").click()
    window.actions.selection_action.trigger()

    assert window.view.interaction_mode == InteractionMode.SELECT
    assert checked_tools(window) == {InteractionMode.SELECT}


def test_measuring_unchecks_tools_and_tool_ends_measuring(window):
    tool_button(window, "Verschieben").click()

    window.actions.distance_measurement_action.trigger()
    assert window.view.measurement_active
    assert checked_tools(window) == set()

    tool_button(window, "Verschieben").click()
    assert not window.view.measurement_active
    assert window.measurement_controller.mode == MeasurementMode.INACTIVE
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
    tool_button(window, "Verschieben").click()
    qapp.processEvents()

    assert window.debug_dock.interaction_mode_value.text() == "Nodes verschieben"


def test_node_group_lists_all_node_tools_in_order(window):
    texts = [action.text() for action in window.actions.tool_panel.tool_buttons]

    assert texts == [
        "Erstellen", "Verschieben", "Rotieren", "Löschen",
        "Verbinden (Regular)", "Verbinden (Dual)", "Verbinden (Reverse)",
    ]


def test_tool_buttons_follow_mode_changes_from_code(window):
    window.set_interaction_mode(InteractionMode.CONNECT_DUAL)

    assert checked_tools(window) == {InteractionMode.CONNECT_DUAL}
