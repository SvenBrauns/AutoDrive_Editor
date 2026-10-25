import math

from dataclasses import dataclass

from PySide6.QtCore import QPointF

from measurement.measurement_mode import MeasurementMode


@dataclass(frozen=True)
class MeasurementResult:
    mode: MeasurementMode
    value: float

    @property
    def unit(self) -> str:
        return self.mode.unit

    @property
    def display_text(self) -> str:
        if self.mode == MeasurementMode.DISTANCE:
            return f"{self.value:.2f} m"

        if self.mode == MeasurementMode.ANGLE:
            return f"{self.value:.2f}°"

        return ""


def calculate_distance(start_position: QPointF, end_position: QPointF) -> float:
    delta_x = end_position.x() - start_position.x()

    delta_z = end_position.y() - start_position.y()

    return math.hypot(delta_x, delta_z)


def calculate_map_angle(start_position: QPointF, end_position: QPointF) -> float:
    delta_x = end_position.x() - start_position.x()

    delta_z = end_position.y() - start_position.y()

    if math.isclose(delta_x, 0.0, abs_tol=0.000001) and math.isclose(
        delta_z, 0.0, abs_tol=0.000001
    ):
        raise ValueError("Für identische Punkte kann kein Richtungswinkel berechnet werden.")

    angle = math.degrees(math.atan2(delta_x, -delta_z))

    normalized_angle = angle % 360.0

    if math.isclose(normalized_angle, 360.0, abs_tol=0.000001) or math.isclose(
        normalized_angle, 0.0, abs_tol=0.000001
    ):
        return 0.0

    return normalized_angle


def calculate_horizontal_alignment_rotation(
    start_position: QPointF, end_position: QPointF
) -> float:
    map_angle = calculate_map_angle(start_position=start_position, end_position=end_position)

    target_view_rotation = (90.0 - map_angle) % 360.0

    if math.isclose(target_view_rotation, 360.0, abs_tol=0.000001):
        return 0.0

    if math.isclose(target_view_rotation, 0.0, abs_tol=0.000001):
        return 0.0

    return target_view_rotation


def calculate_measurement(
    measurement_mode: MeasurementMode, start_position: QPointF, end_position: QPointF
) -> MeasurementResult:
    if not isinstance(measurement_mode, MeasurementMode):
        raise TypeError("Der Messmodus ist ungültig.")

    if not isinstance(start_position, QPointF):
        raise TypeError("Der Startpunkt ist ungültig.")

    if not isinstance(end_position, QPointF):
        raise TypeError("Der Endpunkt ist ungültig.")

    if measurement_mode == MeasurementMode.DISTANCE:
        measurement_value = calculate_distance(start_position, end_position)

    elif measurement_mode == MeasurementMode.ANGLE:
        measurement_value = calculate_map_angle(start_position, end_position)

    else:
        raise ValueError("Im inaktiven Messmodus kann keine Messung berechnet werden.")

    return MeasurementResult(mode=measurement_mode, value=measurement_value)
