"""Marker tools, dock and names on the map in the main window."""

import pytest
from drawing_helpers import shown_marker_names
from mouse_helpers import click, drag, press_escape, view_pos
from PySide6.QtCore import QPoint, Qt

from autodrive_editor.model.autodrive_data import MarkerData, MarkerGroup
from autodrive_editor.ui.tools.interaction_mode import InteractionMode


@pytest.fixture
def marker_window(zoomed_window, qapp):
    """Nodes 1 (x=0), 2 (x=10), 3 (x=20); marker "Hof" on node 1."""

    window = zoomed_window
    data = window.project_coordinator.autodrive_data
    data.marker_groups = [MarkerGroup("All", 1)]
    data.add_marker(MarkerData(1, "Hof", "All"))
    window.marker_dock.set_data(data)

    window.questions = []
    window.answer = ("Silo", "All")

    def ask(title, marker, group, groups, taken_names):
        window.questions.append((title, marker.name if marker else None, group, taken_names))
        return window.answer

    window._ask_marker = ask
    window.data = data
    return window


def at(window, node_x):
    return view_pos(window, node_x, 0)


def names(window):
    return [marker.name for marker in window.data.markers.values()]


def use(window, mode):
    window.set_interaction_mode(mode)


def test_add_marker_asks_and_adds_at_the_end(marker_window):
    use(marker_window, InteractionMode.ADD_MARKER)

    click(marker_window, at(marker_window, 10))

    assert names(marker_window) == ["Hof", "Silo"]
    title, _, group, taken = marker_window.questions[0]
    assert (title, group, taken) == ("Add marker", "All", {("Hof", "All")})
    assert "Silo" in marker_window.status.text()


def test_same_name_in_another_group_can_be_added(marker_window):
    marker_window.answer = ("Hof", "Felder")
    use(marker_window, InteractionMode.ADD_MARKER)

    click(marker_window, at(marker_window, 10))

    assert names(marker_window) == ["Hof", "Hof"]
    assert group_texts(marker_window) == ["All (1)", "Felder (1)"]


def test_add_on_marked_node_does_not_ask(marker_window):
    use(marker_window, InteractionMode.ADD_MARKER)

    click(marker_window, at(marker_window, 0))

    assert marker_window.questions == []
    assert "already" in marker_window.status.text()


def test_cancelled_dialog_changes_nothing(marker_window):
    marker_window.answer = None
    use(marker_window, InteractionMode.ADD_MARKER)

    click(marker_window, at(marker_window, 10))

    assert names(marker_window) == ["Hof"]
    assert not marker_window.edit_history.can_undo


def test_next_marker_suggests_last_group(marker_window):
    marker_window.answer = ("Feld 7", "Felder")
    use(marker_window, InteractionMode.ADD_MARKER)
    click(marker_window, at(marker_window, 10))

    marker_window.answer = None
    click(marker_window, at(marker_window, 20))

    assert marker_window.questions[1][2] == "Felder"


def test_edit_marker_and_undo(marker_window):
    marker_window.answer = ("Hof Nord", "Hof")
    use(marker_window, InteractionMode.EDIT_MARKER)

    click(marker_window, at(marker_window, 0))

    assert marker_window.questions[0][:2] == ("Edit marker", "Hof")
    assert marker_window.data.markers[1].group == "Hof"

    marker_window.edit_history.undo()
    assert (marker_window.data.markers[1].name, marker_window.data.markers[1].group) == (
        "Hof",
        "All",
    )


def test_edit_without_marker_says_so(marker_window):
    use(marker_window, InteractionMode.EDIT_MARKER)

    click(marker_window, at(marker_window, 10))

    assert marker_window.questions == []
    assert "has no marker" in marker_window.status.text()


def test_delete_marker_keeps_the_node(marker_window):
    use(marker_window, InteractionMode.DELETE_MARKER)

    click(marker_window, at(marker_window, 0))

    assert names(marker_window) == []
    assert 1 in marker_window.data.nodes

    marker_window.edit_history.undo()
    assert names(marker_window) == ["Hof"]


def test_move_marker_with_two_clicks(marker_window):
    use(marker_window, InteractionMode.MOVE_MARKER)

    click(marker_window, at(marker_window, 0))
    assert "target node" in marker_window.status.text()

    click(marker_window, at(marker_window, 20))

    assert list(marker_window.data.markers) == [3]
    assert marker_window.data.markers[3].name == "Hof"
    assert marker_window.marker_operation.move_source_id is None


def test_picked_up_marker_node_is_selected_until_the_move(marker_window):
    marker_window.node_selection.replace({2}, 2)
    use(marker_window, InteractionMode.MOVE_MARKER)

    click(marker_window, at(marker_window, 0))
    assert marker_window.node_selection.selected_node_ids == {1}

    click(marker_window, at(marker_window, 20))
    assert marker_window.node_selection.selected_node_ids == {2}


@pytest.mark.parametrize("finish", ["escape", "click_source", "other_tool"])
def test_cancelled_move_restores_the_selection(marker_window, finish):
    marker_window.node_selection.replace({2, 3}, 3)
    use(marker_window, InteractionMode.MOVE_MARKER)
    click(marker_window, at(marker_window, 0))

    if finish == "escape":
        press_escape(marker_window)
    elif finish == "click_source":
        click(marker_window, at(marker_window, 0))
    else:
        use(marker_window, InteractionMode.NAVIGATE)

    assert marker_window.node_selection.selected_node_ids == {2, 3}
    assert marker_window.node_selection.primary_node_id == 3


@pytest.mark.parametrize("cancel", ["escape", "right_click"])
def test_move_can_be_cancelled(marker_window, cancel):
    use(marker_window, InteractionMode.MOVE_MARKER)
    click(marker_window, at(marker_window, 0))

    if cancel == "escape":
        press_escape(marker_window)
    else:
        click(marker_window, at(marker_window, 10), button=Qt.RightButton)

    click(marker_window, at(marker_window, 20))

    assert list(marker_window.data.markers) == [1]


def test_move_onto_marked_node_is_refused(marker_window):
    marker_window.data.add_marker(MarkerData(2, "Silo", "All"))
    use(marker_window, InteractionMode.MOVE_MARKER)

    click(marker_window, at(marker_window, 0))
    click(marker_window, at(marker_window, 10))

    assert list(marker_window.data.markers) == [1, 2]
    assert "already" in marker_window.status.text()


def test_dragging_pans_instead_of_acting(marker_window):
    use(marker_window, InteractionMode.DELETE_MARKER)
    start = at(marker_window, 0)

    drag(marker_window, start, start + QPoint(60, 0))

    assert names(marker_window) == ["Hof"]


# --- names on the map -------------------------------------------------------


def test_marker_shows_its_name(marker_window):
    assert shown_marker_names(marker_window) == {1: "Hof"}


def test_names_can_be_hidden_and_the_choice_is_kept(marker_window):
    marker_window.actions.marker_names_action.setChecked(False)

    assert shown_marker_names(marker_window) == {}
    assert not marker_window.settings.marker_names_visible

    marker_window.actions.marker_names_action.setChecked(True)
    assert marker_window.settings.marker_names_visible


def test_renamed_marker_label_updates(marker_window):
    marker_window.answer = ("Hof Süd", "All")
    use(marker_window, InteractionMode.EDIT_MARKER)

    click(marker_window, at(marker_window, 0))

    assert shown_marker_names(marker_window) == {1: "Hof Süd"}


def test_added_and_moved_markers_are_drawn(marker_window):
    # Far enough in that the names of neighboring nodes do not overlap.
    marker_window.view.set_zoom_level(8.0)
    use(marker_window, InteractionMode.ADD_MARKER)
    click(marker_window, at(marker_window, 10))
    assert shown_marker_names(marker_window) == {1: "Hof", 2: "Silo"}

    use(marker_window, InteractionMode.MOVE_MARKER)
    click(marker_window, at(marker_window, 10))
    click(marker_window, at(marker_window, 20))

    assert shown_marker_names(marker_window) == {1: "Hof", 3: "Silo"}


# --- dock -------------------------------------------------------------------------


def group_texts(window):
    tree = window.marker_dock.tree
    return [tree.topLevelItem(i).text(0) for i in range(tree.topLevelItemCount())]


def test_dock_lists_groups_and_follows_edits(marker_window):
    assert group_texts(marker_window) == ["All (1)"]

    marker_window.answer = ("Feld 7", "Felder")
    use(marker_window, InteractionMode.ADD_MARKER)
    click(marker_window, at(marker_window, 10))
    assert group_texts(marker_window) == ["All (1)", "Felder (1)"]

    marker_window.edit_history.undo()
    assert group_texts(marker_window) == ["All (1)"]


def test_dock_follows_node_deletion(marker_window):
    marker_window.node_selection.replace({1}, 1)

    marker_window.delete_selection()

    assert group_texts(marker_window) == ["All (0)"]


def test_clicking_a_marker_centers_and_selects_it(marker_window):
    marker_window.view.set_zoom_level(40)
    marker_window.view.centerOn(20, 0)
    item = marker_window.marker_dock.marker_item(1)

    marker_window.marker_dock.tree.itemClicked.emit(item, 0)

    # Without a map the view cannot scroll past the outermost node, so
    # only check that the marker is in view.
    assert marker_window.view.get_visible_scene_rect().contains(0, 0)
    assert marker_window.node_selection.selected_node_ids == {1}


def test_double_click_edits_the_marker(marker_window):
    marker_window.answer = ("Hof West", "All")
    item = marker_window.marker_dock.marker_item(1)

    marker_window.marker_dock.tree.itemDoubleClicked.emit(item, 0)

    assert marker_window.data.markers[1].name == "Hof West"


def test_group_can_be_renamed_from_the_dock(marker_window, monkeypatch):
    monkeypatch.setattr(marker_window, "_ask_group_name", lambda name: "Betrieb")
    dock = marker_window.marker_dock
    dock.tree.setCurrentItem(dock.group_item("All"))

    dock.rename_button.click()

    assert group_texts(marker_window) == ["Betrieb (1)"]
    assert marker_window.data.markers[1].group == "Betrieb"


def test_only_empty_groups_can_be_deleted_from_the_dock(marker_window):
    marker_window.data.marker_groups.append(MarkerGroup("Leer", 2))
    dock = marker_window.marker_dock
    dock.set_data(marker_window.data)

    dock.tree.setCurrentItem(dock.group_item("All"))
    assert not dock.delete_button.isEnabled()

    dock.tree.setCurrentItem(dock.group_item("Leer"))
    dock.delete_button.click()

    assert group_texts(marker_window) == ["All (1)"]


def test_dock_is_empty_without_markers(window):
    tree = window.marker_dock.tree

    assert tree.topLevelItem(0).text(0) == window.marker_dock.EMPTY_TEXT
