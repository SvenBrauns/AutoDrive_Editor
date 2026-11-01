"""The fixed toolbar at the top of the window."""

from PySide6.QtWidgets import QCheckBox

from autodrive_editor.terrain.background_map import Background


def toolbar_items(window):
    """The toolbar's buttons in order: action texts, widgets by their attribute name."""
    actions = window.actions
    toolbar = actions.quick_access_toolbar
    widgets = {
        id(actions.background_button): "Background",
        id(actions.grid_controls): "Grid",
        id(actions.rotation_controls): "Rotation",
    }
    items = []

    for action in toolbar.actions():
        widget = toolbar.widgetForAction(action)

        if action.isSeparator():
            items.append("|")
        elif id(widget) in widgets:
            items.append(widgets[id(widget)])
        elif widget is not None and hasattr(widget, "defaultAction") and widget.defaultAction():
            items.append(widget.defaultAction().text().split(":")[0])
        elif action.text():
            items.append(action.text())

    return items


def test_toolbar_order(window):
    assert toolbar_items(window) == [
        "Open…",
        "Save",
        "|",
        "Undo",
        "Redo",
        "|",
        "Copy",
        "Cut",
        "Paste",
        "Background",
        "Grid",
        "Snap to grid",
        "Rotation",
        "Refresh game picture tiles",
        "|",
        "Planning mode",
    ]


def test_background_button_lists_the_three_backgrounds(window):
    actions = window.actions
    menu = actions.background_button.menu()

    assert menu.actions() == [actions.background_actions[b] for b in Background]
    assert not actions.background_button.icon().isNull()


def test_grid_popup_has_no_snap_entry(window):
    texts = [box.text() for box in window.actions.grid_controls.grid_menu.findChildren(QCheckBox)]

    assert texts == ["Show grid"]


def test_open_and_save_have_icons(window):
    assert not window.actions.open_action.icon().isNull()
    assert not window.actions.save_xml_action.icon().isNull()
