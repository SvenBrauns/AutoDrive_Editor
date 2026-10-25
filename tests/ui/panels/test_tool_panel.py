import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QToolButton

from autodrive_editor.measurement.mode import MeasurementMode
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
    assert tool_button(window, "Verschieben").isVisible()


def test_clicking_move_tool_activates_it(window):
    tool_button(window, "Verschieben").click()

    assert window.view.interaction_mode == InteractionMode.MOVE_NODES
    assert checked_tools(window) == {InteractionMode.MOVE_NODES}
    assert window.status.text().startswith("Modus: Nodes verschieben – ")


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


def test_tool_buttons_follow_mode_changes_from_code(window):
    window.set_interaction_mode(InteractionMode.CONNECT_DUAL)

    assert checked_tools(window) == {InteractionMode.CONNECT_DUAL}


# --- layout: icons, two columns, groups, labels, shortcuts --------------


def nodes_group(window):
    return window.actions.tool_panel.groups["Nodes"]


def grid_text(window, row, column):
    item = nodes_group(window).grid.itemAtPosition(row, column)
    return None if item is None else item.widget().defaultAction().text()


def test_node_tools_are_paired_in_two_columns(window):
    layout = [[grid_text(window, row, column) for column in (0, 1)] for row in range(6)]

    assert layout == [
        ["Verschieben", "Verbinden (Regular)"],
        ["Erstellen (Regular)", "Verbinden (Dual)"],
        ["Erstellen (Subprio)", "Verbinden (Reverse)"],
        ["Typ wechseln", "Richtung umkehren"],
        ["Rotieren", "Löschen"],
        ["Position eingeben", None],
    ]


def test_tool_buttons_show_icons_only_by_default(window):
    for action, button in window.actions.tool_panel.tool_buttons.items():
        assert not action.icon().isNull(), action.text()
        assert button.toolButtonStyle() == Qt.ToolButtonIconOnly


def test_tooltips_name_tool_and_shortcut(window):
    tooltip = window.actions.tool_actions[InteractionMode.MOVE_NODES].toolTip()

    assert "<b>Verschieben</b> (V)" in tooltip
    assert "verschieben" in tooltip


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
    assert text.startswith(f"Modus: {mode.display_name} – ")
    assert len(text) > len(f"Modus: {mode.display_name} – ") + 10


def test_panel_widens_for_labels_and_shrinks_again(window, qapp):
    panel = window.actions.tool_panel
    icons_only = panel.width()

    window.actions.tool_labels_action.trigger()
    qapp.processEvents()
    with_labels = panel.width()

    window.actions.tool_labels_action.trigger()
    qapp.processEvents()

    assert with_labels > icons_only + 50
    assert panel.width() == icons_only


def test_undo_icon_is_blue_when_usable_and_light_when_not(window):
    from collections import Counter

    from PySide6.QtGui import QColor, QIcon

    icon = window.actions.undo_action.icon()

    def main_color(mode):
        # The most common opaque color, ignoring smoothed edges.
        image = icon.pixmap(48, 48, mode).toImage()
        colors = Counter(
            QColor.fromRgba(image.pixel(x, y)).name()
            for x in range(image.width())
            for y in range(image.height())
            if QColor.fromRgba(image.pixel(x, y)).alpha() == 255
        )
        return QColor(colors.most_common(1)[0][0])

    usable = main_color(QIcon.Mode.Normal)
    unusable = main_color(QIcon.Mode.Disabled)

    assert usable.blue() > usable.red() + 80  # clearly blue
    assert unusable.lightness() > 190  # very light grey
    assert unusable.lightness() - usable.lightness() > 60
