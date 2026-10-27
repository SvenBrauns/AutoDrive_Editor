"""The network check in the main window."""

import pytest

# The tests change the saved tolerances and ignores.
pytestmark = pytest.mark.usefixtures("isolated_user_data")


@pytest.fixture
def check_window(window, write_xml, qapp):
    """Nodes 1 and 2 overlap (1 -> 2 -> 4), node 3 lies outside the
    2048 m map, node 4 is a normal node."""

    path = write_xml(
        x="0;0.05;1500;10", y="0;0;0;0", z="0;0;0;0", out="2;4;;", incoming=";1;;2", flags="0;0;0;0"
    )
    window.project_coordinator.load_xml_file(path)
    qapp.processEvents()
    window.data = window.project_coordinator.autodrive_data
    return window


def test_check_menu_shows_the_results_in_the_dock(check_window):
    assert check_window.check_dock.isHidden()

    check_window.actions.check_network_action.trigger()

    dock = check_window.check_dock
    assert dock.isVisible()
    assert dock.summary.text() == "Problems found: 2"
    assert dock.group_item(0).child(0).text(0) == "Nodes 1, 2"
    assert dock.group_item(1).child(0).text(0) == "Node 3"


def test_clicking_a_result_selects_its_nodes(check_window):
    check_window.network_check.run()

    item = check_window.check_dock.group_item(0).child(0)
    check_window.check_dock.tree.itemClicked.emit(item, 0)

    assert check_window.node_selection.selected_node_ids == {1, 2}


def test_fix_all_fixes_every_problem_with_one_undo_step_each(check_window):
    check_window.network_check.run()

    check_window.check_dock.fix_all_button.click()

    data = check_window.data
    assert set(data.nodes) == {1, 3, 4}
    assert data.nodes[1].outgoing == {4}
    assert data.nodes[3].x == 1023
    assert check_window.check_dock.summary.text() == "No problems found"

    check_window.edit_history.undo()
    assert data.nodes[3].x == 1500
    assert set(data.nodes) == {1, 3, 4}

    check_window.edit_history.undo()
    assert set(data.nodes) == {1, 2, 3, 4}


def test_heights_are_checked_with_a_heightmap(check_window, sloped_heightmap):
    check_window.heightmap.load(sloped_heightmap)

    check_window.network_check.run()

    heights = check_window.check_dock.group_item(2)
    assert heights.childCount() == 3  # all nodes on the map lie far below the terrain

    check_window.check_dock.fix_all_button.click()

    node = check_window.data.nodes[4]
    assert node.y == pytest.approx(check_window._get_terrain_height(node.x, node.z))


def test_tolerances_are_saved(check_window):
    check_window.check_dock.overlap_box.setValue(0.5)

    assert check_window.settings.check_tolerances[0] == 0.5


def test_loading_new_data_clears_the_results(check_window, write_xml):
    check_window.network_check.run()

    check_window.project_coordinator.load_xml_file(write_xml())

    assert check_window.check_dock.tree.topLevelItemCount() == 0


def select(dock, group, child=None):
    dock.tree.clearSelection()
    item = dock.group_item(group)
    (item if child is None else item.child(child)).setSelected(True)


def test_ignored_entries_move_to_the_ignored_group(check_window):
    dock = check_window.check_dock
    check_window.network_check.run()

    select(dock, 1, 0)
    dock.ignore_button.click()

    assert dock.summary.text() == "Problems found: 1"
    assert dock.group_item(1).childCount() == 0
    assert dock.group_item(3).text(0) == "Ignored (1)"

    dock.fix_all_button.click()

    assert check_window.data.nodes[3].x == 1500  # ignored entries are not fixed

    select(dock, 3)
    dock.unignore_button.click()

    assert dock.group_item(1).childCount() == 1
    assert dock.tree.topLevelItemCount() == 3


def test_ignores_are_kept_when_the_network_is_opened_again(check_window, qapp):
    dock = check_window.check_dock
    check_window.network_check.run()
    select(dock, 0, 0)
    dock.ignore_button.click()
    dock.check_boxes["outside"].setChecked(False)

    check_window.project_coordinator.load_xml_file(
        check_window.project_coordinator.config_source.path
    )
    qapp.processEvents()
    check_window.network_check.run()

    assert not dock.check_boxes["outside"].isChecked()
    assert dock.group_item(0).childCount() == 0
    assert dock.group_item(1).text(0) == "Nodes outside the map: switched off"
    assert dock.group_item(3).child(0).text(0) == "Nodes 1, 2"


def test_ignored_entry_comes_back_after_moving_a_node(check_window):
    dock = check_window.check_dock
    check_window.network_check.run()
    select(dock, 1, 0)
    dock.ignore_button.click()

    check_window.data.nodes[3].x = 1600
    check_window.network_check.run()

    assert dock.group_item(1).childCount() == 1
