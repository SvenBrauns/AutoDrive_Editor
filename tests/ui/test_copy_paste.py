"""Copy, cut and paste in the main window."""

import pytest

from autodrive_editor.model.autodrive_data import MarkerData


@pytest.fixture
def paste_window(loaded_window):
    """Nodes 1 (x=0) -> 2 (x=10) -> 3 (x=20) on z=0; marker on 2."""

    window = loaded_window
    window.data = window.project_coordinator.autodrive_data
    window.data.add_marker(MarkerData(2, "Silo", "All"))
    window.paste_at = (100.0, 50.0)
    window._get_paste_position = lambda: window.paste_at
    return window


def positions(window, node_ids):
    return sorted((window.data.nodes[i].x, window.data.nodes[i].z) for i in node_ids)


def test_copy_and_paste_centered_on_the_mouse(paste_window):
    paste_window.node_selection.replace({1, 2})

    paste_window.actions.copy_action.trigger()
    paste_window.actions.paste_action.trigger()

    assert set(paste_window.data.nodes) == {1, 2, 3, 4, 5}
    assert positions(paste_window, {4, 5}) == [(95, 50), (105, 50)]
    assert paste_window.data.nodes[4].outgoing == {5}
    assert paste_window.node_selection.selected_node_ids == {4, 5}
    assert paste_window.status.text() == "2 Nodes eingefügt"


def test_pasted_markers_appear_in_the_dock(paste_window):
    paste_window.node_selection.replace({2})
    paste_window.actions.copy_action.trigger()

    paste_window.actions.paste_action.trigger()

    names = sorted(marker.name for marker in paste_window.data.markers.values())
    assert names == ["Silo", "Silo (2)"]
    assert paste_window.marker_dock.group_item("All").childCount() == 2


def test_paste_at_original_position(paste_window):
    paste_window.node_selection.replace({1, 2})
    paste_window.actions.copy_action.trigger()

    paste_window.actions.paste_at_original_action.trigger()

    assert positions(paste_window, {4, 5}) == [(0, 0), (10, 0)]


def test_paste_is_one_undo_step(paste_window):
    paste_window.node_selection.replace({1, 2, 3})
    paste_window.actions.copy_action.trigger()
    paste_window.actions.paste_action.trigger()

    paste_window.edit_history.undo()

    assert set(paste_window.data.nodes) == {1, 2, 3}
    assert list(paste_window.data.markers) == [2]


def test_cut_removes_the_selection_and_can_be_pasted(paste_window):
    paste_window.node_selection.replace({3})

    paste_window.actions.cut_action.trigger()
    assert set(paste_window.data.nodes) == {1, 2}
    assert paste_window.status.text() == "1 Node ausgeschnitten"

    paste_window.actions.paste_action.trigger()
    assert positions(paste_window, {3}) == [(100, 50)]  # freed id 3 is used again


def test_clipboard_survives_loading_other_data(paste_window, write_xml):
    paste_window.node_selection.replace({1, 2})
    paste_window.actions.copy_action.trigger()

    paste_window.project_coordinator.load_xml_file(
        write_xml(x="0", y="0", z="0", out="", incoming="", flags="0")
    )
    paste_window.data = paste_window.project_coordinator.autodrive_data
    paste_window.actions.paste_action.trigger()

    assert set(paste_window.data.nodes) == {1, 2, 3}


def test_copy_without_selection_says_so(paste_window):
    paste_window.actions.copy_action.trigger()

    assert paste_window.status.text() == "Keine Nodes ausgewählt"


def test_paste_with_empty_clipboard_says_so(paste_window):
    paste_window.actions.paste_action.trigger()

    assert paste_window.status.text() == "Die Zwischenablage ist leer"
    assert not paste_window.edit_history.can_undo


def test_shortcuts_are_the_usual_ones(paste_window):
    actions = paste_window.actions

    assert actions.copy_action.shortcut().toString() == "Ctrl+C"
    assert actions.cut_action.shortcut().toString() == "Ctrl+X"
    assert actions.paste_action.shortcut().toString() == "Ctrl+V"
    assert actions.paste_at_original_action.shortcut().toString() == "Ctrl+Shift+V"
