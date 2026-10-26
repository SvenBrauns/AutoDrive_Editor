from collections.abc import Callable

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QGraphicsView

from autodrive_editor.i18n import tr


class ViewRotationController(QObject):
    """Rotates the view around its center, optionally in fixed steps."""

    rotation_changed = Signal(float)

    rotation_step_changed = Signal(float)

    ROTATION_DEGREES_PER_PIXEL = 0.3
    ROTATION_COMPARISON_TOLERANCE = 0.000001
    DEFAULT_ROTATION_STEP = 1.0

    MAXIMUM_ROTATION_STEP = 90.0

    def __init__(self, view: QGraphicsView, viewport_update_callback: Callable, parent=None):
        super().__init__(parent)

        if not isinstance(view, QGraphicsView):
            raise TypeError("Invalid map view.")

        if not callable(viewport_update_callback):
            raise TypeError("Invalid viewport update callback.")

        self.view = view

        self._viewport_update_callback = viewport_update_callback

        self._rotation_angle = 0.0
        self._raw_rotation_angle = 0.0

        self._rotation_step = self.DEFAULT_ROTATION_STEP

    @property
    def rotation_angle(self) -> float:
        return self._rotation_angle

    @property
    def rotation_step(self) -> float:
        return self._rotation_step

    def set_rotation_angle(self, rotation_angle: float):
        self._raw_rotation_angle = self._normalize_rotation_angle(rotation_angle)

        target_angle = self._snap_rotation_angle(self._raw_rotation_angle)

        self._apply_rotation_angle(target_angle)

    def set_exact_rotation_angle(self, rotation_angle: float):
        target_angle = self._normalize_rotation_angle(rotation_angle)

        self._raw_rotation_angle = target_angle

        self._apply_rotation_angle(target_angle)

    def set_rotation_step(self, rotation_step: float):
        rotation_step = float(rotation_step)

        if rotation_step < 0.0:
            raise ValueError(tr("The rotation step must not be negative."))

        if rotation_step > self.MAXIMUM_ROTATION_STEP:
            raise ValueError(tr("The rotation step must be at most 90 degrees."))

        if abs(rotation_step - self._rotation_step) < self.ROTATION_COMPARISON_TOLERANCE:
            return

        self._rotation_step = rotation_step

        target_angle = self._snap_rotation_angle(self._raw_rotation_angle)

        self._apply_rotation_angle(target_angle)

        self.rotation_step_changed.emit(self._rotation_step)

    def reset_rotation(self):
        self._raw_rotation_angle = 0.0

        self._apply_rotation_angle(0.0)

    def rotate_by_horizontal_pixels(self, horizontal_pixel_delta: float):
        rotation_delta = float(horizontal_pixel_delta) * self.ROTATION_DEGREES_PER_PIXEL

        if abs(rotation_delta) < self.ROTATION_COMPARISON_TOLERANCE:
            return

        self._raw_rotation_angle = self._normalize_rotation_angle(
            self._raw_rotation_angle + rotation_delta
        )

        target_angle = self._snap_rotation_angle(self._raw_rotation_angle)

        self._apply_rotation_angle(target_angle)

    def _apply_rotation_angle(self, target_angle: float):
        target_angle = self._normalize_rotation_angle(target_angle)

        rotation_delta = (target_angle - self._rotation_angle + 180.0) % 360.0 - 180.0

        if abs(rotation_delta) < self.ROTATION_COMPARISON_TOLERANCE:
            return

        viewport_center = self.view.viewport().rect().center()

        scene_center = self.view.mapToScene(viewport_center)

        self.view.rotate(rotation_delta)

        self._rotation_angle = target_angle

        self.view.centerOn(scene_center)

        self.rotation_changed.emit(self._rotation_angle)

        self._viewport_update_callback()

    @staticmethod
    def _normalize_rotation_angle(rotation_angle: float) -> float:
        normalized_angle = float(rotation_angle) % 360.0

        if (
            abs(normalized_angle) < ViewRotationController.ROTATION_COMPARISON_TOLERANCE
            or abs(normalized_angle - 360.0) < ViewRotationController.ROTATION_COMPARISON_TOLERANCE
        ):
            return 0.0

        return normalized_angle

    def _snap_rotation_angle(self, rotation_angle: float) -> float:
        if self._rotation_step <= self.ROTATION_COMPARISON_TOLERANCE:
            return self._normalize_rotation_angle(rotation_angle)

        snapped_angle = round(rotation_angle / self._rotation_step) * self._rotation_step

        return self._normalize_rotation_angle(snapped_angle)
