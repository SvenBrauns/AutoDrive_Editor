"""Snapping to the grid while creating and moving nodes."""

import pytest
from mouse_helpers import click, drag, view_pos

from autodrive_editor.ui.tools.interaction_mode import InteractionMode


@pytest.fixture
def snap_window(zoomed_window):
    zoomed_window.actions.grid_snap_action.setChecked(True)
    zoomed_window.data = zoomed_window.project_coordinator.autodrive_data
    return zoomed_window


def xz(window, node_id):
    node = window.data.nodes[node_id]
    return round(node.x, 6), round(node.z, 6)


def test_created_node_lands_on_the_grid(snap_window):
    snap_window.set_interaction_mode(InteractionMode.CREATE_NODES)

    click(snap_window, view_pos(snap_window, 13, 18))

    assert xz(snap_window, 4) == (10, 20)


def test_grabbed_node_snaps_and_selection_keeps_its_shape(snap_window):
    snap_window.node_selection.replace({2, 3})
    snap_window.set_interaction_mode(InteractionMode.MOVE_NODES)

    drag(snap_window, view_pos(snap_window, 10, 0), view_pos(snap_window, 13, 8))

    assert xz(snap_window, 2) == (10, 10)
    assert xz(snap_window, 3) == (20, 10)
    assert xz(snap_window, 1) == (0, 0)


def test_grid_spacing_is_used(snap_window):
    snap_window.grid_coordinator.set_grid_spacing(4.0)
    snap_window.set_interaction_mode(InteractionMode.CREATE_NODES)

    click(snap_window, view_pos(snap_window, 13, 18))

    assert xz(snap_window, 4) == (12, 16)


def test_without_snapping_positions_are_free(snap_window):
    snap_window.actions.grid_snap_action.setChecked(False)
    snap_window.set_interaction_mode(InteractionMode.CREATE_NODES)

    click(snap_window, view_pos(snap_window, 13, 18))

    x, z = xz(snap_window, 4)
    assert abs(x - 13) < 0.5 and abs(z - 18) < 0.5


def test_checkbox_shortcut_and_button_stay_in_sync(snap_window):
    controls = snap_window.actions.grid_controls
    assert controls.snap_input.isChecked()
    assert controls.isChecked()
    assert snap_window.actions.grid_snap_action.shortcut().toString() == "G"

    controls.snap_input.setChecked(False)

    assert not snap_window.actions.grid_snap_action.isChecked()
    assert not snap_window.background_map.grid_snap_enabled
    assert controls.isChecked()
    assert snap_window.status.text() == "Snap off"


def test_grid_button_toggles_grid(snap_window):
    controls = snap_window.actions.grid_controls

    controls.click()

    assert not controls.isChecked()
    assert not controls.visibility_input.isChecked()
    assert not snap_window.background_map.grid_visible

    controls.visibility_input.setChecked(True)

    assert controls.isChecked()
    assert snap_window.background_map.grid_visible
