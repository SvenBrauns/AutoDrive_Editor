from dataclasses import dataclass

from PySide6.QtCore import QPointF


@dataclass
class MeasurementPoint:
    """A measurement point: either a free map position or anchored to a node."""

    position: QPointF
    node_id: int | None = None

    def __post_init__(self):
        self.position = QPointF(self.position)

    @property
    def is_free_point(self) -> bool:
        return self.node_id is None

    @property
    def x(self) -> float:
        return self.position.x()

    @property
    def z(self) -> float:
        return self.position.y()

    def set_position(self, position: QPointF):
        if not self.is_free_point:
            raise ValueError("A measuring point bound to a node cannot be moved freely.")

        self.position = QPointF(position)

    def copy(self) -> "MeasurementPoint":
        return MeasurementPoint(self.position, self.node_id)
