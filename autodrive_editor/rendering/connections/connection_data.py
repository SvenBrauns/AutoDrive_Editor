from dataclasses import dataclass

from PySide6.QtCore import QRectF

from autodrive_editor.model.connections import ConnectionType


@dataclass(frozen=True)
class ConnectionData:
    """A connection with the positions of both nodes, as stored in the connection index."""

    source_id: int
    target_id: int

    source_x: float
    source_z: float

    target_x: float
    target_z: float

    connection_type: ConnectionType

    @property
    def key(self) -> tuple[ConnectionType, int, int]:
        if self.connection_type == ConnectionType.DUAL:
            return (
                self.connection_type,
                min(self.source_id, self.target_id),
                max(self.source_id, self.target_id),
            )

        return (self.connection_type, self.source_id, self.target_id)

    @property
    def minimum_x(self) -> float:
        return min(self.source_x, self.target_x)

    @property
    def maximum_x(self) -> float:
        return max(self.source_x, self.target_x)

    @property
    def minimum_z(self) -> float:
        return min(self.source_z, self.target_z)

    @property
    def maximum_z(self) -> float:
        return max(self.source_z, self.target_z)

    def intersects_rect(self, rect: QRectF) -> bool:
        return not (
            self.maximum_x < rect.left()
            or self.minimum_x > rect.right()
            or self.maximum_z < rect.top()
            or self.minimum_z > rect.bottom()
        )
