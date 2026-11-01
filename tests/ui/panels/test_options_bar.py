from PySide6.QtWidgets import QWidget

from autodrive_editor.ui.panels.options_bar import OptionsBar
from autodrive_editor.ui.tools.interaction_mode import InteractionMode


def test_shows_the_tool_name_and_its_options(qapp):
    bar = OptionsBar()
    options = QWidget()
    bar.add_options([InteractionMode.DRAW_LINE, InteractionMode.DRAW_ARC], options)

    bar.show_tool(InteractionMode.DRAW_ARC)

    assert bar.name_label.text() == "Arc"
    assert bar.stack.currentWidget() is options


def test_a_tool_without_options_shows_only_its_name(qapp):
    bar = OptionsBar()
    bar.add_options([InteractionMode.DRAW_LINE], QWidget())

    bar.show_tool(InteractionMode.MOVE_NODES)

    assert bar.name_label.text() == "Move nodes"
    assert bar.stack.currentWidget() is bar.no_options


def test_the_window_shows_the_active_tool_in_the_options_bar(window):
    window.set_interaction_mode(InteractionMode.DELETE_NODES)

    assert window.options_bar.name_label.text() == "Delete nodes"
    assert window.options_bar.isVisible()


def test_no_tool_button_has_an_arrow_menu(window):
    buttons = list(window.actions.tool_panel.tool_buttons.values())
    toolbar = window.actions.quick_access_toolbar
    buttons.append(toolbar.widgetForAction(window.actions.generate_action))

    assert all(button.menu() is None for button in buttons)
