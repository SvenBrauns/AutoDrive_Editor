from PySide6.QtGui import QAction
from PySide6.QtWidgets import QToolButton, QWidget

from autodrive_editor.ui.panels.options_bar import OptionsBar
from autodrive_editor.ui.tools.interaction_mode import InteractionMode


def test_shows_the_tool_name_and_its_options(qapp):
    bar = OptionsBar()
    options = QWidget()
    bar.add_options([InteractionMode.DRAW_LINE, InteractionMode.DRAW_ARC], options)

    bar.show_tool(InteractionMode.DRAW_ARC)

    assert bar.name_label.text() == "Draw"
    assert bar.stack.currentWidget() is options


def test_a_tool_without_options_shows_only_its_name(qapp):
    bar = OptionsBar()
    bar.add_options([InteractionMode.DRAW_LINE], QWidget())

    bar.show_tool(InteractionMode.MOVE_NODES)

    assert bar.name_label.text() == "Move nodes"
    assert bar.stack.currentWidget() is bar.no_options


def test_the_window_shows_the_active_tool_in_the_options_bar(window):
    window.set_interaction_mode(InteractionMode.TOGGLE_NODE_TYPE)

    assert window.options_bar.name_label.text() == "Toggle node type"
    assert window.options_bar.isVisible()


def test_no_tool_button_has_an_arrow_menu(window):
    strip = window.actions.tool_strip
    buttons = [strip.widgetForAction(a) for a in strip.actions() if not a.isSeparator()]

    assert all(button.menu() is None for button in buttons)


def test_variant_buttons_show_only_for_their_tool(qapp):
    bar = OptionsBar()
    actions = {
        InteractionMode.CREATE_NODES: QAction("R"),
        InteractionMode.CREATE_SUBPRIO_NODES: QAction("S"),
    }
    bar.add_variants(actions)
    variants = bar.variants[InteractionMode.CREATE_NODES]

    bar.show_tool(InteractionMode.CREATE_SUBPRIO_NODES)

    assert bar.name_label.text() == "Create"
    assert not variants.isHidden()
    assert [b.defaultAction() for b in variants.findChildren(QToolButton)] == list(actions.values())

    bar.show_tool(InteractionMode.MOVE_NODES)

    assert variants.isHidden()


def test_the_window_shows_the_variant_buttons_of_the_active_tool(window):
    window.set_interaction_mode(InteractionMode.MOVE_MARKER)
    variants = window.options_bar.variants[InteractionMode.MOVE_MARKER]
    buttons = variants.findChildren(QToolButton)

    assert window.options_bar.name_label.text() == "Marker"
    assert [b.defaultAction().text() for b in buttons] == [
        "Marker – Add",
        "Marker – Edit",
        "Marker – Move",
        "Marker – Delete",
    ]
    assert [b.isChecked() for b in buttons] == [False, False, True, False]
