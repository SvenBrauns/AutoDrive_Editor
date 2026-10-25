import pytest

from PySide6.QtCore import QPointF

from measurement.measurement_math import (
    calculate_distance,
    calculate_horizontal_alignment_rotation,
    calculate_map_angle,
    calculate_measurement
)
from measurement.measurement_mode import MeasurementMode


ORIGIN = QPointF(0, 0)


def test_distance_is_euclidean():
    assert calculate_distance(ORIGIN, QPointF(3, 4)) == pytest.approx(5.0)


def test_distance_of_identical_points_is_zero():
    assert calculate_distance(QPointF(7, 7), QPointF(7, 7)) == 0.0


# Scene y is the map z axis. Negative z points north (up on the map).
@pytest.mark.parametrize(
    ("end", "expected_angle"),
    [
        (QPointF(0, -10), 0.0),     # north
        (QPointF(10, 0), 90.0),     # east
        (QPointF(0, 10), 180.0),    # south
        (QPointF(-10, 0), 270.0),   # west
        (QPointF(10, -10), 45.0),   # north-east
    ]
)
def test_map_angle_is_clockwise_from_north(end, expected_angle):
    assert calculate_map_angle(ORIGIN, end) == pytest.approx(expected_angle)


def test_map_angle_of_identical_points_raises():
    with pytest.raises(ValueError):
        calculate_map_angle(ORIGIN, QPointF(0, 0))


def test_map_angle_just_west_of_north_does_not_return_360():
    angle = calculate_map_angle(ORIGIN, QPointF(-1e-9, -10))

    assert 0.0 <= angle < 360.0


@pytest.mark.parametrize(
    ("end", "expected_rotation"),
    [
        (QPointF(10, 0), 0.0),      # already horizontal (east)
        (QPointF(0, -10), 90.0),    # north
        (QPointF(0, 10), 270.0),    # south
        (QPointF(-10, 0), 180.0),   # west
    ]
)
def test_horizontal_alignment_rotation(end, expected_rotation):
    rotation = calculate_horizontal_alignment_rotation(ORIGIN, end)

    assert rotation == pytest.approx(expected_rotation)


def test_calculate_measurement_distance_result():
    result = calculate_measurement(MeasurementMode.DISTANCE, ORIGIN, QPointF(3, 4))

    assert result.value == pytest.approx(5.0)
    assert result.unit == "m"
    assert result.display_text == "5.00 m"


def test_calculate_measurement_angle_result():
    result = calculate_measurement(MeasurementMode.ANGLE, ORIGIN, QPointF(10, 0))

    assert result.value == pytest.approx(90.0)
    assert result.display_text == "90.00°"


def test_calculate_measurement_rejects_inactive_mode():
    with pytest.raises(ValueError):
        calculate_measurement(MeasurementMode.INACTIVE, ORIGIN, QPointF(1, 1))


def test_calculate_measurement_rejects_wrong_point_type():
    with pytest.raises(TypeError):
        calculate_measurement(MeasurementMode.DISTANCE, (0, 0), QPointF(1, 1))
