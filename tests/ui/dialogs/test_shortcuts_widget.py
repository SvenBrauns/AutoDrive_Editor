from PySide6.QtGui import QAction, QKeySequence

from autodrive_editor.ui.actions.shortcuts import ShortcutRegistry
from autodrive_editor.ui.dialogs.shortcuts_widget import ShortcutsWidget


def make_widget(qapp, answer=True):
    registry = ShortcutRegistry()

    for name, key in (("save", "Ctrl+S"), ("open", "Ctrl+O"), ("exit", "")):
        action = QAction(name.title())
        action.setShortcut(QKeySequence(key))
        registry.add(name, "File", action)

    widget = ShortcutsWidget(registry)
    widget.questions = []
    widget._ask_move = lambda key, text: widget.questions.append((key, text)) or answer

    return widget


def test_shows_the_current_keys_grouped_by_menu(qapp):
    widget = make_widget(qapp)

    group = widget.tree.topLevelItem(0)
    assert group.text(0) == "File"
    assert group.child(0).text(0) == "Save"
    assert widget.edits["save"].keySequence().toString() == "Ctrl+S"
    assert widget.edits["exit"].keySequence().isEmpty()


def test_new_key_is_reported_as_changed(qapp):
    widget = make_widget(qapp)

    widget.edits["exit"].setKeySequence(QKeySequence("Ctrl+Q"))
    widget.edits["save"].clear()

    assert widget.changed_keys() == {"exit": ["Ctrl+Q"], "save": []}


def test_used_key_moves_after_asking(qapp):
    widget = make_widget(qapp)

    widget.edits["exit"].setKeySequence(QKeySequence("Ctrl+S"))

    assert widget.questions == [("Ctrl+S", "Save")]
    assert widget.changed_keys() == {"exit": ["Ctrl+S"], "save": []}
    assert widget.edits["save"].keySequence().isEmpty()


def test_used_key_stays_when_declined(qapp):
    widget = make_widget(qapp, answer=False)

    widget.edits["exit"].setKeySequence(QKeySequence("Ctrl+S"))

    assert widget.changed_keys() == {}
    assert widget.edits["exit"].keySequence().isEmpty()


def test_reset_all_restores_the_defaults(qapp):
    widget = make_widget(qapp)
    widget.edits["exit"].setKeySequence(QKeySequence("Ctrl+S"))

    widget.reset_all()

    assert widget.changed_keys() == {}
    assert widget.edits["save"].keySequence().toString() == "Ctrl+S"
