from PySide6.QtGui import QAction, QKeySequence

from autodrive_editor.ui.actions.shortcuts import ShortcutRegistry, find_conflict


def make_registry(qapp):
    save = QAction("Save")
    save.setShortcut(QKeySequence("Ctrl+S"))
    redo = QAction("Redo")
    redo.setShortcuts([QKeySequence("Ctrl+Y"), QKeySequence("Ctrl+Shift+Z")])

    registry = ShortcutRegistry()
    registry.add("save", "File", save)
    registry.add("redo", "Edit", redo, "Redo last step")

    return registry, save, redo


def test_add_keeps_the_current_shortcuts_as_defaults(qapp):
    registry, _, _ = make_registry(qapp)

    assert registry.entries["save"].default_keys == ("Ctrl+S",)
    assert registry.entries["redo"].default_keys == ("Ctrl+Y", "Ctrl+Shift+Z")
    assert registry.entries["redo"].text == "Redo last step"


def test_apply_sets_changed_keys_and_restores_the_others(qapp):
    registry, save, redo = make_registry(qapp)

    registry.apply({"save": ["F2"], "redo": [], "unknown": ["F3"]})
    assert registry.current_keys() == {"save": ["F2"], "redo": []}

    registry.apply({})
    assert save.shortcut().toString() == "Ctrl+S"
    assert len(redo.shortcuts()) == 2


def test_changed_keys_leaves_out_defaults_and_unknown_actions(qapp):
    registry, _, _ = make_registry(qapp)

    keys = {"save": ["Ctrl+S"], "redo": ["Ctrl+Y"], "unknown": ["F3"]}

    assert registry.changed_keys(keys) == {"redo": ["Ctrl+Y"]}


def test_find_conflict_names_the_other_action():
    keys = {"save": ["Ctrl+S"], "redo": ["Ctrl+Y", "Ctrl+Shift+Z"]}

    assert find_conflict(keys, "save", "Ctrl+Shift+Z") == "redo"
    assert find_conflict(keys, "save", "Ctrl+S") is None
    assert find_conflict(keys, "save", "F2") is None
