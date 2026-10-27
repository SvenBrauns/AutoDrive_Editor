import pytest

from autodrive_editor.network_check.checks import CheckResults, HeightProblem
from autodrive_editor.ui.panels.check_dock import CheckDock

RESULTS = CheckResults([[1, 2], [5, 6, 7]], [9], [HeightProblem(4, 30.0, 10.0)])
IGNORED = CheckResults([], [8], [])


@pytest.fixture
def dock(qapp):
    dock = CheckDock(0.1, 5.0)
    dock.set_results(RESULTS)
    yield dock
    dock.deleteLater()


def texts(item):
    return [item.child(i).text(0) for i in range(item.childCount())]


def test_shows_one_group_per_kind_of_problem(dock):
    assert dock.summary.text() == "Problems found: 4"
    assert dock.group_item(0).text(0) == "Overlapping nodes (2)"
    assert texts(dock.group_item(0)) == ["Nodes 1, 2", "Nodes 5, 6, 7"]
    assert texts(dock.group_item(1)) == ["Node 9"]
    assert texts(dock.group_item(2)) == ["Node 4: 30.0 m, terrain 10.0 m"]


def test_without_heightmap_the_heights_are_marked_as_not_checked(dock):
    dock.set_results(CheckResults([], [], None))

    assert dock.summary.text() == "No problems found"
    assert dock.group_item(2).text(0) == "Heights not checked: no heightmap loaded"
    assert not dock.fix_all_button.isEnabled()


def test_clearing_resets_the_list(dock):
    dock.set_results(None)

    assert dock.tree.topLevelItemCount() == 0
    assert dock.summary.text() == "The network has not been checked yet"


def test_clicking_an_entry_activates_its_nodes(dock):
    activated = []
    dock.nodes_activated.connect(activated.append)

    for group, child in ((0, 1), (1, 0), (2, 0)):
        item = dock.group_item(group).child(child)
        dock.tree.itemClicked.emit(item, 0)

    assert activated == [[5, 6, 7], [9], [4]]


def test_fix_all_requests_every_problem(dock):
    requested = []
    dock.fix_requested.connect(requested.append)

    dock.fix_all_button.click()

    assert requested == [RESULTS]


def test_fix_selected_requests_selected_entries_and_groups(dock):
    requested = []
    dock.fix_requested.connect(requested.append)
    assert not dock.fix_selected_button.isEnabled()

    dock.group_item(0).child(1).setSelected(True)
    dock.group_item(2).setSelected(True)
    dock.group_item(2).child(0).setSelected(True)  # also part of the selected group
    dock.fix_selected_button.click()

    assert requested == [CheckResults([[5, 6, 7]], [], [HeightProblem(4, 30.0, 10.0)])]


def test_changing_a_tolerance_is_reported(dock):
    changes = []
    dock.tolerances_changed.connect(lambda *values: changes.append(values))

    dock.height_box.setValue(2.5)

    assert changes == [(0.1, 2.5)]
    assert dock.tolerances == (0.1, 2.5)


def test_ignored_entries_are_shown_collapsed_and_not_fixed(dock):
    requested = []
    dock.fix_requested.connect(requested.append)

    dock.set_results(RESULTS, IGNORED)
    dock.fix_all_button.click()

    ignored_group = dock.group_item(3)
    assert ignored_group.text(0) == "Ignored (1)"
    assert texts(ignored_group) == ["Node 8"]
    assert not ignored_group.isExpanded()
    assert requested == [RESULTS]


def test_ignore_and_unignore_request_only_their_kind_of_entry(dock):
    ignore, unignore = [], []
    dock.ignore_requested.connect(ignore.append)
    dock.unignore_requested.connect(unignore.append)
    dock.set_results(RESULTS, IGNORED)

    dock.group_item(1).child(0).setSelected(True)
    assert dock.ignore_button.isEnabled()
    assert not dock.unignore_button.isEnabled()

    dock.group_item(3).setSelected(True)
    dock.ignore_button.click()
    dock.unignore_button.click()

    assert ignore == [CheckResults([], [9], [])]
    assert unignore == [IGNORED]


def test_switched_off_checks(dock):
    changes = []
    dock.checks_changed.connect(changes.append)

    dock.check_boxes["height"].setChecked(False)
    dock.set_results(CheckResults([[1, 2]], [], []))

    assert changes == [{"overlap", "outside"}]
    assert dock.group_item(2).text(0) == "Height differs from the terrain: switched off"


def test_setting_the_checks_is_not_reported_as_a_change(dock):
    changes = []
    dock.checks_changed.connect(changes.append)

    dock.set_enabled_checks({"overlap"})

    assert dock.enabled_checks == {"overlap"}
    assert changes == []
