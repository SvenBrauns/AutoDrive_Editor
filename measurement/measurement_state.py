from dataclasses import dataclass

from PySide6.QtCore import QPointF

from measurement.measurement_math import MeasurementResult, calculate_measurement
from measurement.measurement_mode import MeasurementMode
from measurement.measurement_point import MeasurementPoint


@dataclass
class MeasurementState:
    mode: MeasurementMode = MeasurementMode.INACTIVE

    start_point: MeasurementPoint | None = None
    end_point: MeasurementPoint | None = None
    preview_position: QPointF | None = None

    def __post_init__(self):
        if not isinstance(self.mode, MeasurementMode):
            raise TypeError("Der Messmodus ist ungültig.")

        if self.start_point is not None and not isinstance(self.start_point, MeasurementPoint):
            raise TypeError("Der Startpunkt ist ungültig.")

        if self.end_point is not None and not isinstance(self.end_point, MeasurementPoint):
            raise TypeError("Der Endpunkt ist ungültig.")

        if self.preview_position is not None and not isinstance(self.preview_position, QPointF):
            raise TypeError("Die Vorschauposition ist ungültig.")

        if self.preview_position is not None:
            self.preview_position = QPointF(self.preview_position)

    @property
    def is_active(self) -> bool:
        return self.mode != MeasurementMode.INACTIVE

    @property
    def has_start_point(self) -> bool:
        return self.start_point is not None

    @property
    def has_end_point(self) -> bool:
        return self.end_point is not None

    @property
    def is_complete(self) -> bool:
        return self.is_active and self.start_point is not None and self.end_point is not None

    @property
    def is_awaiting_start_point(self) -> bool:
        return self.is_active and self.start_point is None

    @property
    def is_awaiting_end_point(self) -> bool:
        return self.is_active and self.start_point is not None and self.end_point is None

    @property
    def display_end_position(self) -> QPointF | None:
        if self.end_point is not None:
            return QPointF(self.end_point.position)

        if self.preview_position is not None:
            return QPointF(self.preview_position)

        return None

    def activate(self, mode: MeasurementMode):
        if not isinstance(mode, MeasurementMode):
            raise TypeError("Der Messmodus ist ungültig.")

        if mode == MeasurementMode.INACTIVE:
            raise ValueError("Zum Aktivieren muss ein aktiver Messmodus angegeben werden.")

        self.mode = mode
        self.clear_points()

    def deactivate(self):
        self.mode = MeasurementMode.INACTIVE
        self.clear_points()

    def clear_points(self):
        self.start_point = None
        self.end_point = None
        self.preview_position = None

    def set_start_point(self, measurement_point: MeasurementPoint):
        self._validate_active_mode()

        if not isinstance(measurement_point, MeasurementPoint):
            raise TypeError("Der Startpunkt ist ungültig.")

        self.start_point = measurement_point.copy()

        self.end_point = None
        self.preview_position = None

    def set_end_point(self, measurement_point: MeasurementPoint):
        self._validate_active_mode()

        if self.start_point is None:
            raise ValueError("Vor dem Endpunkt muss zuerst ein Startpunkt gesetzt werden.")

        if not isinstance(measurement_point, MeasurementPoint):
            raise TypeError("Der Endpunkt ist ungültig.")

        self.end_point = measurement_point.copy()

        self.preview_position = None

    def set_preview_position(self, position: QPointF | None):
        self._validate_active_mode()

        if self.start_point is None:
            self.preview_position = None
            return

        if self.end_point is not None:
            self.preview_position = None
            return

        if position is None:
            self.preview_position = None
            return

        if not isinstance(position, QPointF):
            raise TypeError("Die Vorschauposition ist ungültig.")

        self.preview_position = QPointF(position)

    def move_free_point(self, point_index: int, position: QPointF):
        self._validate_active_mode()

        measurement_point = self._get_point(point_index)

        measurement_point.set_position(position)

    def calculate_result(self, include_preview: bool = False) -> MeasurementResult | None:
        if self.start_point is None:
            return None

        if self.end_point is not None:
            end_position = self.end_point.position

        elif include_preview and self.preview_position is not None:
            end_position = self.preview_position

        else:
            return None

        try:
            return calculate_measurement(
                measurement_mode=self.mode,
                start_position=(self.start_point.position),
                end_position=end_position,
            )

        except ValueError:
            return None

    def get_point(self, point_index: int) -> MeasurementPoint | None:
        if point_index == 0:
            return self.start_point

        if point_index == 1:
            return self.end_point

        raise IndexError("Ein Messpunktindex muss 0 oder 1 sein.")

    def _get_point(self, point_index: int) -> MeasurementPoint:
        measurement_point = self.get_point(point_index)

        if measurement_point is None:
            raise ValueError("Der angeforderte Messpunkt ist noch nicht gesetzt.")

        return measurement_point

    def _validate_active_mode(self):
        if not self.is_active:
            raise ValueError("Der Messmodus ist nicht aktiv.")
