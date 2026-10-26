import pytest
from mouse_helpers import click, drag, press_escape, view_pos
from PySide6.QtCore import QPoint

from autodrive_editor.measurement.mode import MeasurementMode

FREE = (5, 20)  # map position between the nodes, below the line


@pytest.fixture
def measuring(zoomed_window):
    zoomed_window.set_measurement_mode(MeasurementMode.DISTANCE)
    return zoomed_window


def test_clicks_on_nodes_anchor_the_points(measuring):
    click(measuring, view_pos(measuring, 0, 0))
    click(measuring, view_pos(measuring, 20, 0))

    state = measuring.measurement_coordinator.state
    assert (state.start_point.node_id, state.end_point.node_id) == (1, 3)
    assert state.calculate_result().value == pytest.approx(20.0)


def test_node_anchored_point_is_not_grabbed(measuring):
    click(measuring, view_pos(measuring, 0, 0))
    click(measuring, view_pos(measuring, *FREE))

    coordinator = measuring.measurement_coordinator
    coordinator.handle_press(view_pos(measuring, 0, 0), None)

    assert not coordinator.is_point_dragging


def test_escape_during_drag_puts_the_point_back(measuring):
    click(measuring, view_pos(measuring, 0, 0))
    click(measuring, view_pos(measuring, *FREE))
    coordinator = measuring.measurement_coordinator
    before = coordinator.state.end_point.position
    start = view_pos(measuring, *FREE)

    drag(measuring, start, start + QPoint(40, 0), release=False)
    assert coordinator.state.end_point.position != before
    press_escape(measuring)

    assert not coordinator.is_point_dragging
    assert coordinator.state.end_point.position == before
    assert coordinator.is_complete


def test_measurement_stays_when_data_is_loaded_again(measuring, write_xml):
    click(measuring, view_pos(measuring, *FREE))
    click(measuring, view_pos(measuring, 15, 25))

    measuring.project_coordinator.load_xml_file(write_xml())

    coordinator = measuring.measurement_coordinator
    assert coordinator.is_complete
    assert all(item.scene() is measuring.scene for item in coordinator._items)
