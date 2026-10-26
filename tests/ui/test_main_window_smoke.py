"""Smoke tests: build the real main window headless and drive the main
signal paths, so wiring mistakes between parts fail here instead of
only showing up as console errors in the running app."""

from dataclasses import replace

import pytest
from mouse_helpers import click
from PySide6.QtCore import QPoint, QRectF, Qt
from PySide6.QtGui import QPainterPath

from autodrive_editor.editing.commands.move_nodes import MoveNodesCommand
from autodrive_editor.measurement.mode import MeasurementMode
from autodrive_editor.ui.main_window import MainWindow
from autodrive_editor.ui.tools.interaction_mode import InteractionMode


def test_window_starts(window):
    assert window.status.text() == MainWindow.NO_FILE_STATUS


def test_rotation_updates_reset_action(window, qapp):
    window.view.set_rotation_angle(30)
    qapp.processEvents()
    assert window.actions.reset_rotation_action.isEnabled()

    window.reset_view_rotation()
    qapp.processEvents()
    assert not window.actions.reset_rotation_action.isEnabled()


def test_measurement_clicks_create_complete_measurement(window, qapp):
    window.set_measurement_mode(MeasurementMode.DISTANCE)
    assert window.view.measurement_active

    click(window, QPoint(300, 300))
    click(window, QPoint(450, 380))
    qapp.processEvents()

    assert window.measurement_coordinator.is_complete


def test_grid_controls_update_grid_and_status(window):
    controls = window.actions.grid_controls

    controls.spacing_requested.emit(25.0)
    assert window.background_map.grid_spacing == 25.0
    assert "25.00" in window.status.text()

    controls.reset_requested.emit()
    assert window.background_map.grid_spacing == 10.0


def test_debug_dock_refreshes_on_zoom(window, qapp):
    window.debug_dock.show()
    qapp.processEvents()

    zoom_levels = []
    original = window.debug_dock.set_view_state

    def record(**kwargs):
        zoom_levels.append(kwargs["zoom_level"])
        original(**kwargs)

    window.debug_dock.set_view_state = record

    window.view.set_zoom_level(2.0)
    qapp.processEvents()

    assert zoom_levels and zoom_levels[-1] == pytest.approx(2.0)


def test_load_xml_reports_waypoint_count(loaded_window):
    assert len(loaded_window.project_coordinator.autodrive_data) == 3
    assert "3 waypoints" in loaded_window.status.text()


def test_area_selection_selects_nodes(loaded_window, qapp):
    loaded_window.set_interaction_mode(InteractionMode.SELECT)

    path = QPainterPath()
    path.addRect(QRectF(-5, -5, 20, 10))  # covers nodes 1 (x=0) and 2 (x=10)

    loaded_window.selection_coordinator.handle_area(path, Qt.NoModifier)
    qapp.processEvents()

    selection = loaded_window.node_selection
    assert selection.selected_node_ids == {1, 2}
    assert selection.primary_node_id == 1


def push_move(window, end_x):
    data = window.project_coordinator.autodrive_data
    node = data.get_node(1)
    window.edit_history.push(
        MoveNodesCommand(data, {1: (node.x, node.y, node.z)}, {1: (end_x, node.y, node.z)})
    )


def test_undo_actions_start_disabled(window):
    assert not window.actions.undo_action.isEnabled()
    assert not window.actions.redo_action.isEnabled()
    assert window.actions.undo_action.text() == "Undo"


def test_undo_action_follows_history(loaded_window):
    actions = loaded_window.actions
    node = loaded_window.project_coordinator.autodrive_data.get_node(1)

    push_move(loaded_window, 50)
    assert actions.undo_action.isEnabled()
    assert actions.undo_action.text() == "Undo: Move node"
    assert loaded_window.isWindowModified()

    actions.undo_action.trigger()
    assert node.x == 0
    assert actions.redo_action.text() == "Redo: Move node"
    assert not loaded_window.isWindowModified()

    actions.redo_action.trigger()
    assert node.x == 50


def test_loading_xml_clears_undo_history(loaded_window, write_xml):
    push_move(loaded_window, 50)

    loaded_window.project_coordinator.load_xml_file(write_xml())

    assert not loaded_window.actions.undo_action.isEnabled()
    assert not loaded_window.isWindowModified()


def test_display_style_is_applied_without_rebuilding_the_scene(zoomed_window):
    window = zoomed_window
    renderer = window.scene_renderer
    node_layer = renderer.node_layer
    window.node_selection.replace({2}, 2)

    style = replace(renderer.display_style, node_diameter=renderer.display_style.node_diameter * 2)
    window.apply_display_style(style)

    assert renderer.node_layer is node_layer
    assert all(layer.display_style is style for layer in renderer.layers)
    assert window.node_selection.selected_node_ids == {2}
    assert renderer.get_node_at(10, 0, window.view.zoom_level).node_id == 2
