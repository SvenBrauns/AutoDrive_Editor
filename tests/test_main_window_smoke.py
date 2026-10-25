"""Smoke tests: build the real main window headless and drive the main
signal paths, so wiring mistakes between parts fail here instead of
only showing up as console errors in the running app."""

import pytest

from PySide6.QtCore import QPoint, QRectF, Qt
from PySide6.QtGui import QPainterPath

from measurement.measurement_mode import MeasurementMode
from ui.interaction_mode import InteractionMode
from ui.main_window import MainWindow


@pytest.fixture
def window(qapp):
    main_window = MainWindow()
    main_window.show()
    qapp.processEvents()

    yield main_window

    main_window.close()
    main_window.deleteLater()
    qapp.processEvents()


@pytest.fixture
def loaded_window(window, write_xml, qapp):
    path = write_xml(x="0;10;20", z="0;0;0", out="2;3;", incoming=";1;2")
    window.project_coordinator.load_xml_file(path)
    qapp.processEvents()
    return window


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

    for position in (QPoint(50, 50), QPoint(150, 120)):
        window.view.measurement_press_requested.emit(position, Qt.NoModifier)
        window.view.measurement_release_requested.emit(position, Qt.NoModifier)

    qapp.processEvents()
    assert window.measurement_controller.is_complete

    window.view.measurement_cancel_requested.emit()


def test_grid_controls_update_grid_and_status(window):
    controls = window.actions.grid_controls

    controls.spacing_requested.emit(25.0)
    assert window.background_manager.grid_spacing == 25.0
    assert "25.00" in window.status.text()

    controls.reset_requested.emit()
    assert window.background_manager.grid_spacing == 10.0


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
    assert "3 Waypoints" in loaded_window.status.text()


def test_area_selection_selects_nodes(loaded_window, qapp):
    loaded_window.set_interaction_mode(InteractionMode.SELECT)

    path = QPainterPath()
    path.addRect(QRectF(-5, -5, 20, 10))  # covers nodes 1 (x=0) and 2 (x=10)

    loaded_window.view.selection_area_requested.emit(path, Qt.NoModifier)
    qapp.processEvents()

    selection = loaded_window.node_selection_manager
    assert selection.selected_node_ids == {1, 2}
    assert selection.primary_node_id == 1
