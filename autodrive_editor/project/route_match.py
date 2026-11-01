"""Whether the open network is kept as a route: the savegame does not store which route it came
from, so a route counts as the same network if it has the same nodes at the same positions."""

from autodrive_editor.model.autodrive_data import AutoDriveData

# Routes exported by AutoDrive have 2 decimals, savegames 3.
TOLERANCE = 0.011


def same_network(a: AutoDriveData, b: AutoDriveData) -> bool:
    if len(a.nodes) != len(b.nodes):
        return False

    return all(
        abs(p - q) <= TOLERANCE
        for first, second in zip(_positions(a), _positions(b), strict=True)
        for p, q in zip(first, second, strict=True)
    )


def _positions(data: AutoDriveData) -> list[tuple[float, float, float]]:
    return sorted((node.x, node.z, node.y) for node in data.nodes.values())
