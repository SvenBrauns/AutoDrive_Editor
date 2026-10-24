from dataclasses import dataclass


@dataclass(frozen=True)
class ConnectionRenderData:

    source_id: int
    target_id: int

    source_x: float
    source_z: float

    target_x: float
    target_z: float

    connection_type: str

    @property
    def key(self):
        if self.connection_type == "dual":
            return (
                self.connection_type,
                min(
                    self.source_id,
                    self.target_id
                ),
                max(
                    self.source_id,
                    self.target_id
                )
            )

        return (
            self.connection_type,
            self.source_id,
            self.target_id
        )

    @property
    def minimum_x(self):
        return min(
            self.source_x,
            self.target_x
        )


    @property
    def maximum_x(self):
        return max(
            self.source_x,
            self.target_x
        )


    @property
    def minimum_z(self):
        return min(
            self.source_z,
            self.target_z
        )


    @property
    def maximum_z(self):
        return max(
            self.source_z,
            self.target_z
        )


    def intersects_rect(
        self,
        rect
    ):
        return not (
            self.maximum_x < rect.left()
            or self.minimum_x > rect.right()
            or self.maximum_z < rect.top()
            or self.minimum_z > rect.bottom()
        )