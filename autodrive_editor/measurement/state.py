from dataclasses import dataclass

from PySide6.QtCore import QPointF

from autodrive_editor.measurement.calculations import MeasurementResult, calculate_measurement
from autodrive_editor.measurement.mode import MeasurementMode
from autodrive_editor.measurement.point import MeasurementPoint


@dataclass
class MeasurementState:
    """Points A and B of the current measurement and the rules for setting them. While only A
    is set, the preview position stands in for B."""

    mode: MeasurementMode = MeasurementMode.INACTIVE
    start_point: MeasurementPoint | None = None
    end_point: MeasurementPoint | None = None
    preview_position: QPointF | None = None

    @property
    def is_active(self) -> bool:
        return self.mode != MeasurementMode.INACTIVE

    @property
    def has_start_point(self) -> bool:
        return self.start_point is not None

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
        """Point B, or the preview position while B is not set."""

        if self.end_point is not None:
            return QPointF(self.end_point.position)

        return QPointF(self.preview_position) if self.preview_position is not None else None

    def activate(self, mode: MeasurementMode):
        if mode == MeasurementMode.INACTIVE:
            raise ValueError("Activating needs an active measurement mode.")

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

        self.start_point = measurement_point.copy()
        self.end_point = None
        self.preview_position = None

    def set_end_point(self, measurement_point: MeasurementPoint):
        self._validate_active_mode()

        if self.start_point is None:
            raise ValueError("Point A must be set before point B.")

        self.end_point = measurement_point.copy()
        self.preview_position = None

    def set_preview_position(self, position: QPointF | None):
        """The preview is only kept while point B is missing."""

        self._validate_active_mode()

        if self.is_awaiting_end_point and position is not None:
            self.preview_position = QPointF(position)
        else:
            self.preview_position = None

    def move_free_point(self, point_index: int, position: QPointF):
        self._validate_active_mode()

        measurement_point = self.get_point(point_index)

        if measurement_point is None:
            raise ValueError("The measuring point is not set yet.")

        measurement_point.set_position(position)

    def calculate_result(self, include_preview: bool = False) -> MeasurementResult | None:
        if self.start_point is None:
            return None

        end_position = self.display_end_position if include_preview else None

        if self.end_point is not None:
            end_position = self.end_point.position

        if end_position is None:
            return None

        try:
            return calculate_measurement(self.mode, self.start_point.position, end_position)
        except ValueError:
            return None

    def get_point(self, point_index: int) -> MeasurementPoint | None:
        if point_index not in (0, 1):
            raise IndexError("A measuring point index must be 0 or 1.")

        return self.start_point if point_index == 0 else self.end_point

    def _validate_active_mode(self):
        if not self.is_active:
            raise ValueError("Measuring is not active.")
