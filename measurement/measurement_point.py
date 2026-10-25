from dataclasses import dataclass

from PySide6.QtCore import QPointF


@dataclass
class MeasurementPoint:
    position: QPointF
    node_id: int | None = None

    def __post_init__(self):
        if not isinstance(self.position, QPointF):
            raise TypeError("Die Position des Messpunkts muss ein QPointF sein.")

        self.position = QPointF(self.position)

        if self.node_id is not None:
            self.node_id = int(self.node_id)

            if self.node_id <= 0:
                raise ValueError("Eine Node-ID muss größer als 0 sein.")

    @property
    def is_node_anchor(self) -> bool:
        return self.node_id is not None

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
        if not isinstance(position, QPointF):
            raise TypeError("Die Position des Messpunkts muss ein QPointF sein.")

        if self.is_node_anchor:
            raise ValueError(
                "Ein an eine Node gebundener Messpunkt kann nicht frei verschoben werden."
            )

        self.position = QPointF(position)

    @classmethod
    def create_free(cls, position: QPointF) -> "MeasurementPoint":
        return cls(position=position, node_id=None)

    @classmethod
    def create_node_anchor(cls, node_id: int, position: QPointF) -> "MeasurementPoint":
        return cls(position=position, node_id=node_id)

    def copy(self) -> "MeasurementPoint":
        return MeasurementPoint(position=QPointF(self.position), node_id=self.node_id)
