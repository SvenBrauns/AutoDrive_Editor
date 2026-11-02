"""Planning mode: edits go into a plan that is applied as one undo step or discarded."""

from PySide6.QtWidgets import QMessageBox

from autodrive_editor.editing.commands.delete_nodes import DeleteNodesCommand
from autodrive_editor.editing.commands.move_nodes import MoveNodesCommand
from autodrive_editor.file_io.autodrive_xml import AutoDriveXmlReader


def move_node(window, node_id, x):
    data = window.project_coordinator.autodrive_data
    node = data.nodes[node_id]
    window.edit_history.push(
        MoveNodesCommand(data, {node_id: (node.x, node.y, node.z)}, {node_id: (x, node.y, node.z)})
    )


def node_x(window, node_id):
    return window.project_coordinator.autodrive_data.nodes[node_id].x


def answer(window, button):
    window.planning._ask_end_plan = lambda: button


def test_planning_needs_loaded_data(window):
    assert not window.planning.action.isEnabled()


def test_planning_shows_the_bar_and_blocks_saving(loaded_window):
    window = loaded_window
    window.planning.action.trigger()

    assert window.edit_history.is_planning
    assert window.planning.action.isChecked()
    assert window.planning.bar.isVisible()
    assert not window.actions.save_xml_action.isEnabled()
    assert not window.actions.save_xml_as_action.isEnabled()


def test_changed_nodes_are_highlighted_and_counted(loaded_window):
    window = loaded_window
    window.planning.action.trigger()
    move_node(window, 2, 15)

    assert window.scene_renderer.plan_node_ids == {2}
    assert "1" in window.planning.bar_label.text()

    window.edit_history.undo()
    assert window.scene_renderer.plan_node_ids == set()


def test_applied_plan_is_one_undo_step(loaded_window):
    window = loaded_window
    window.planning.action.trigger()
    move_node(window, 1, 5)
    move_node(window, 3, 25)
    window.planning.apply_button.click()

    assert not window.edit_history.is_planning
    assert not window.planning.bar.isVisible()
    assert window.actions.save_xml_action.isEnabled()
    assert window.scene_renderer.plan_node_ids == set()

    window.edit_history.undo()
    assert (node_x(window, 1), node_x(window, 3)) == (0, 20)


def test_discarded_plan_reverts_its_edits(loaded_window):
    window = loaded_window
    window.planning.action.trigger()
    window.edit_history.push(DeleteNodesCommand(window.project_coordinator.autodrive_data, {2}))
    window.planning.discard_button.click()

    assert 2 in window.project_coordinator.autodrive_data.nodes
    assert not window.edit_history.can_undo


def test_turning_planning_off_asks_and_can_be_cancelled(loaded_window):
    window = loaded_window
    window.planning.action.trigger()
    move_node(window, 2, 15)

    answer(window, QMessageBox.Cancel)
    window.planning.action.trigger()
    assert window.edit_history.is_planning
    assert window.planning.action.isChecked()

    answer(window, QMessageBox.Apply)
    window.planning.action.trigger()
    assert not window.edit_history.is_planning
    assert node_x(window, 2) == 15


def test_plan_without_edits_ends_without_asking(loaded_window):
    window = loaded_window
    window.planning.action.trigger()
    window.planning._ask_end_plan = fail_when_asked

    window.planning.action.trigger()
    assert not window.edit_history.is_planning


def fail_when_asked():
    raise AssertionError("asked although the plan has no edits")


def test_closing_or_opening_asks_about_the_plan_first(loaded_window):
    window = loaded_window
    window.planning.action.trigger()
    move_node(window, 2, 15)

    answer(window, QMessageBox.Cancel)
    assert not window.files.confirm_discard_changes()
    assert window.edit_history.is_planning

    answer(window, QMessageBox.Discard)
    assert window.files.confirm_discard_changes()
    assert node_x(window, 2) == 10


def test_autosave_keeps_the_edits_before_an_open_plan(loaded_window):
    window = loaded_window
    store = window.files.autosave_store
    move_node(window, 1, 5)
    window.planning.action.trigger()
    move_node(window, 2, 123)

    window.files.autosave()
    autosaved = AutoDriveXmlReader.load(store.xml_path)

    assert autosaved.nodes[1].x == 5
    assert autosaved.nodes[2].x != 123


def test_the_map_stays_still_when_the_bar_shows_and_hides(loaded_window, qapp):
    window = loaded_window
    view = window.view
    # A map image makes the scene this large; the view is not held at its edge.
    window.scene.setSceneRect(-1000, -1000, 2000, 2000)
    view.set_zoom_level(4.0)
    view.centerOn(10, 0)
    qapp.processEvents()

    def window_position_of(x, z):
        return view.viewport().mapTo(window, view.mapFromScene(x, z))

    before = window_position_of(10, 0)
    window.planning.start_plan()
    qapp.processEvents()

    assert window.planning.bar.isVisible()
    assert (window_position_of(10, 0) - before).manhattanLength() <= 1

    window.edit_history.discard_plan()
    qapp.processEvents()

    assert (window_position_of(10, 0) - before).manhattanLength() <= 1


def test_the_map_stays_still_when_a_panel_opens_beside_it(loaded_window, qapp):
    window = loaded_window
    view = window.view
    window.scene.setSceneRect(-1000, -1000, 2000, 2000)
    view.set_zoom_level(4.0)
    view.centerOn(10, 0)
    qapp.processEvents()
    before = view.viewport().mapTo(window, view.mapFromScene(10, 0))

    window.debug_dock.show()
    qapp.processEvents()

    assert (view.viewport().mapTo(window, view.mapFromScene(10, 0)) - before).manhattanLength() <= 1
