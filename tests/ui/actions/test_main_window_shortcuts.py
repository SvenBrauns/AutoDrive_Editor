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
    assert entries["tool_measure_distance"].text == "Measure – Distance"
    assert entries["align_measurement"].text == "Align the measuring line horizontally"
    assert {"save_xml", "check_network", "panel_marker_dock", "show_nodes"} <= set(entries)


def test_each_variant_key_is_its_own_entry(clean_window):
    entries = clean_window.actions.shortcuts.entries

    assert entries["tool_create_nodes"].text == "Create – Regular"
    assert entries["tool_create_subprio_nodes"].text == "Create – Subprio"
    assert entries["tool_draw_arc"].text == "Draw – Arc"


def test_a_changed_variant_key_shows_in_the_strip_tooltip(clean_window):
    clean_window.actions.apply_shortcuts({"tool_create_nodes": ["Q"]})
    strip = clean_window.actions.merged_tool_actions

    assert any("<b>Create – Regular</b> (Q)" in a.toolTip() for a in strip.values())


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
