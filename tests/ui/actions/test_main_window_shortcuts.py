"""Changed shortcuts in the running editor."""

import pytest
from PySide6.QtGui import QKeySequence

from autodrive_editor.ui.dialogs.settings_dialog import SettingsDialog
from autodrive_editor.ui.tools.interaction_mode import InteractionMode


@pytest.fixture
def clean_window(isolated_user_data, window):
    return window


def test_all_menu_and_tool_actions_can_be_changed(clean_window):
    actions = clean_window.actions
    entries = actions.shortcuts.entries

    assert entries["tool_move_nodes"].action is actions.tool_actions[InteractionMode.MOVE_NODES]
    assert entries["redo"].default_keys == tuple(
        key.toString() for key in QKeySequence.keyBindings(QKeySequence.Redo)
    )
    assert entries["distance_measurement"].text == "Measure the distance between two points"
    assert {"save_xml", "check_network", "panel_marker_dock", "show_nodes", "map_scale_2"} <= set(
        entries
    )


def test_settings_apply_changed_shortcuts_and_tooltips(clean_window, monkeypatch):
    clean_window.settings.set_shortcuts({"tool_move_nodes": ["M"], "save_xml": []})
    monkeypatch.setattr(SettingsDialog, "exec", lambda dialog: True)

    clean_window.open_settings()

    move = clean_window.actions.tool_actions[InteractionMode.MOVE_NODES]
    assert move.shortcut().toString() == "M"
    assert "<b>Move</b> (M)" in move.toolTip()
    assert clean_window.actions.save_xml_action.shortcut().isEmpty()


def test_tooltip_without_shortcut_has_no_brackets(clean_window):
    clean_window.actions.apply_shortcuts({"tool_move_nodes": []})

    assert (
        "<b>Move</b><br>" in clean_window.actions.tool_actions[InteractionMode.MOVE_NODES].toolTip()
    )
