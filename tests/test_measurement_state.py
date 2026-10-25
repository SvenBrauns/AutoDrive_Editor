import pytest

from PySide6.QtCore import QPointF

from measurement.measurement_mode import MeasurementMode
from measurement.measurement_point import MeasurementPoint
from measurement.measurement_state import MeasurementState


def free(x, z):
    return MeasurementPoint.create_free(QPointF(x, z))


@pytest.fixture
def distance_state():
    state = MeasurementState()
    state.activate(MeasurementMode.DISTANCE)
    return state


def test_new_state_is_inactive():
    state = MeasurementState()

    assert not state.is_active
    assert not state.is_awaiting_start_point


def test_activate_rejects_inactive_mode():
    with pytest.raises(ValueError):
        MeasurementState().activate(MeasurementMode.INACTIVE)


def test_setting_points_requires_active_mode():
    with pytest.raises(ValueError):
        MeasurementState().set_start_point(free(0, 0))


def test_point_workflow(distance_state):
    assert distance_state.is_awaiting_start_point

    distance_state.set_start_point(free(0, 0))
    assert distance_state.is_awaiting_end_point

    distance_state.set_end_point(free(3, 4))
    assert distance_state.is_complete
    assert distance_state.calculate_result().value == pytest.approx(5.0)


def test_end_point_requires_start_point(distance_state):
    with pytest.raises(ValueError):
        distance_state.set_end_point(free(1, 1))


def test_new_start_point_clears_end_point(distance_state):
    distance_state.set_start_point(free(0, 0))
    distance_state.set_end_point(free(1, 1))

    distance_state.set_start_point(free(5, 5))

    assert distance_state.end_point is None


def test_preview_is_used_only_when_requested(distance_state):
    distance_state.set_start_point(free(0, 0))
    distance_state.set_preview_position(QPointF(6, 8))

    assert distance_state.calculate_result() is None
    assert distance_state.calculate_result(include_preview=True).value == pytest.approx(10.0)
    assert distance_state.display_end_position == QPointF(6, 8)


def test_preview_is_ignored_once_end_point_is_set(distance_state):
    distance_state.set_start_point(free(0, 0))
    distance_state.set_end_point(free(3, 4))

    distance_state.set_preview_position(QPointF(100, 100))

    assert distance_state.preview_position is None


def test_points_are_copied(distance_state):
    point = free(0, 0)
    distance_state.set_start_point(point)

    point.set_position(QPointF(50, 50))

    assert distance_state.start_point.position == QPointF(0, 0)


def test_move_free_point_updates_result(distance_state):
    distance_state.set_start_point(free(0, 0))
    distance_state.set_end_point(free(3, 4))

    distance_state.move_free_point(1, QPointF(6, 8))

    assert distance_state.calculate_result().value == pytest.approx(10.0)


def test_node_anchored_point_cannot_be_moved(distance_state):
    distance_state.set_start_point(
        MeasurementPoint.create_node_anchor(node_id=5, position=QPointF(0, 0))
    )

    with pytest.raises(ValueError):
        distance_state.move_free_point(0, QPointF(1, 1))


def test_angle_of_identical_points_gives_no_result():
    state = MeasurementState()
    state.activate(MeasurementMode.ANGLE)
    state.set_start_point(free(2, 2))
    state.set_end_point(free(2, 2))

    assert state.calculate_result() is None


def test_get_point_rejects_invalid_index(distance_state):
    with pytest.raises(IndexError):
        distance_state.get_point(2)


def test_deactivate_clears_points(distance_state):
    distance_state.set_start_point(free(0, 0))

    distance_state.deactivate()

    assert not distance_state.is_active
    assert distance_state.start_point is None
