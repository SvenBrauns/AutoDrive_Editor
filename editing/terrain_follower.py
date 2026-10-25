from collections.abc import Callable


# Returns the terrain height at a map position (x, z), or None if
# there is no heightmap or the position is outside the map.
TerrainHeightProvider = Callable[[float, float], float | None]


class TerrainFollower:
    """Lets moved nodes follow the terrain.

    Each node keeps its distance above the terrain it had when the
    edit started, so nodes on the ground stay on the ground and nodes
    on bridges stay above it. Without terrain information the height
    is left unchanged.
    """

    def __init__(
        self,
        terrain_height_at: TerrainHeightProvider | None = None
    ):
        self.terrain_height_at = terrain_height_at

        self._offsets: dict[int, float] = {}

    def begin(
        self,
        start_positions: dict[int, tuple[float, float, float]]
    ):
        """Remembers each node's height above the terrain."""

        self._offsets = {}

        if self.terrain_height_at is None:
            return

        for node_id, (x, y, z) in start_positions.items():
            terrain_height = self.terrain_height_at(
                x,
                z
            )

            if terrain_height is not None:
                self._offsets[node_id] = (
                    y - terrain_height
                )

    def height_at(
        self,
        node_id: int,
        start_position: tuple[float, float, float],
        new_x: float,
        new_z: float
    ) -> float:
        """Height for a node moved from its start position to
        (new_x, new_z)."""

        start_x, start_y, start_z = start_position

        if (
            (new_x, new_z) == (start_x, start_z)
            or node_id not in self._offsets
        ):
            return start_y

        terrain_height = self.terrain_height_at(
            new_x,
            new_z
        )

        if terrain_height is None:
            return start_y

        return (
            terrain_height
            + self._offsets[node_id]
        )
