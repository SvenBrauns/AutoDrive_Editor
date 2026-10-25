from dataclasses import dataclass

from PySide6.QtCore import QObject, QPointF, Signal


@dataclass
class PointDragState:
    """Where a dragged point started and where it is now."""

    point_index: int | None = None

    press_scene_position: QPointF | None = None
    original_point_position: QPointF | None = None
    current_point_position: QPointF | None = None

    @property
    def is_active(self) -> bool:
        return (
            self.point_index is not None
            and self.press_scene_position is not None
            and self.original_point_position is not None
            and self.current_point_position is not None
        )

    def begin(
        self, point_index: int, press_scene_position: QPointF, original_point_position: QPointF
    ):
        if point_index < 0:
            raise ValueError("Der Punktindex darf nicht negativ sein.")

        if not isinstance(press_scene_position, QPointF):
            raise TypeError("Die Scene-Position des Klicks ist ungültig.")

        if not isinstance(original_point_position, QPointF):
            raise TypeError("Die Ausgangsposition des Punkts ist ungültig.")

        self.point_index = int(point_index)

        self.press_scene_position = QPointF(press_scene_position)

        self.original_point_position = QPointF(original_point_position)

        self.current_point_position = QPointF(original_point_position)

    def update(self, current_scene_position: QPointF) -> QPointF:
        if not self.is_active:
            raise RuntimeError("Es ist kein Point-Drag aktiv.")

        if not isinstance(current_scene_position, QPointF):
            raise TypeError("Die aktuelle Scene-Position ist ungültig.")

        movement = current_scene_position - self.press_scene_position

        self.current_point_position = self.original_point_position + movement

        return QPointF(self.current_point_position)

    def reset(self):
        self.point_index = None
        self.press_scene_position = None
        self.original_point_position = None
        self.current_point_position = None


class PointDragController(QObject):
    """Drags a single point by the mouse movement since the press."""

    drag_started = Signal(int, QPointF)

    position_requested = Signal(int, QPointF)

    drag_finished = Signal(int, QPointF)

    drag_cancelled = Signal(int, QPointF)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._state = PointDragState()

    @property
    def is_active(self) -> bool:
        return self._state.is_active

    @property
    def active_point_index(self) -> int | None:
        return self._state.point_index

    def begin_drag(
        self, point_index: int, press_scene_position: QPointF, original_point_position: QPointF
    ):
        if self.is_active:
            self.cancel_drag()

        self._state.begin(
            point_index=point_index,
            press_scene_position=press_scene_position,
            original_point_position=original_point_position,
        )

        self.drag_started.emit(point_index, QPointF(original_point_position))

    def update_drag(self, current_scene_position: QPointF) -> QPointF | None:
        if not self.is_active:
            return None

        requested_position = self._state.update(current_scene_position)

        self.position_requested.emit(self._state.point_index, QPointF(requested_position))

        return requested_position

    def finish_drag(self) -> QPointF | None:
        if not self.is_active:
            return None

        point_index = self._state.point_index

        final_position = QPointF(self._state.current_point_position)

        self._state.reset()

        self.drag_finished.emit(point_index, QPointF(final_position))

        return final_position

    def cancel_drag(self) -> QPointF | None:
        if not self.is_active:
            return None

        point_index = self._state.point_index

        original_position = QPointF(self._state.original_point_position)

        self._state.reset()

        self.drag_cancelled.emit(point_index, QPointF(original_position))

        return original_position
