"""Checks that find problems in an AutoDrive network."""

import math
from collections import defaultdict
from dataclasses import dataclass

from autodrive_editor.model.autodrive_data import AutoDriveData
from autodrive_editor.terrain.heightmap_transform import HeightmapTransform
from autodrive_editor.terrain.terrain_follower import TerrainHeightProvider

# The kinds of checks.
OVERLAP, OUTSIDE, HEIGHT = "overlap", "outside", "height"
ALL_CHECKS = (OVERLAP, OUTSIDE, HEIGHT)


@dataclass(frozen=True)
class HeightProblem:
    """A node whose height differs too much from the terrain."""

    node_id: int
    height: float
    terrain_height: float


@dataclass(frozen=True)
class CheckResults:
    """Problems found by the network check. height_problems is None when
    no heightmap was loaded, so the heights were not checked."""

    overlapping_groups: list[list[int]]
    outside_node_ids: list[int]
    height_problems: list[HeightProblem] | None

    @property
    def problem_count(self) -> int:
        return (
            len(self.overlapping_groups)
            + len(self.outside_node_ids)
            + len(self.height_problems or [])
        )

    def entries(self) -> list[tuple[str, object]]:
        """(kind, problem) of every problem: the node id list of an
        overlapping group, the node id outside the map or the HeightProblem."""

        return (
            [(OVERLAP, group) for group in self.overlapping_groups]
            + [(OUTSIDE, node_id) for node_id in self.outside_node_ids]
            + [(HEIGHT, problem) for problem in self.height_problems or []]
        )

    @classmethod
    def from_entries(cls, entries) -> "CheckResults":
        """Results of (kind, problem) entries; duplicates are left out."""

        problems = {kind: [] for kind in ALL_CHECKS}

        for kind, problem in entries:
            if problem not in problems[kind]:
                problems[kind].append(problem)

        return cls(problems[OVERLAP], problems[OUTSIDE], problems[HEIGHT])


def problem_node_ids(kind: str, problem) -> list[int]:
    """The nodes of an entry from CheckResults.entries()."""

    if kind == OVERLAP:
        return list(problem)

    if kind == OUTSIDE:
        return [problem]

    return [problem.node_id]


def check_network(
    autodrive_data: AutoDriveData,
    map_scale: int,
    terrain_height_at: TerrainHeightProvider | None,
    overlap_tolerance: float,
    max_height_difference: float,
    checks=ALL_CHECKS,
) -> CheckResults:
    """Runs the given checks; the others report nothing. Pass
    terrain_height_at only with a loaded heightmap."""

    if terrain_height_at is None:
        height_problems = None
    elif HEIGHT in checks:
        height_problems = find_height_problems(
            autodrive_data, terrain_height_at, max_height_difference
        )
    else:
        height_problems = []

    return CheckResults(
        overlapping_groups=(
            find_overlapping_nodes(autodrive_data, overlap_tolerance) if OVERLAP in checks else []
        ),
        outside_node_ids=(
            find_nodes_outside_map(autodrive_data, map_scale) if OUTSIDE in checks else []
        ),
        height_problems=height_problems,
    )


def find_overlapping_nodes(autodrive_data: AutoDriveData, tolerance: float) -> list[list[int]]:
    """Groups of nodes that lie within the tolerance of each other (3D
    distance). A node close to any member belongs to the group. Each group
    is sorted, the groups by their smallest id."""

    if tolerance <= 0:
        raise ValueError("The tolerance must be greater than 0.")

    # Nodes by grid cell of the tolerance's size, so each node is only
    # compared with the nodes in its own and the neighboring cells.
    cells = defaultdict(list)

    for node in autodrive_data.nodes.values():
        cells[(math.floor(node.x / tolerance), math.floor(node.z / tolerance))].append(node)

    parents: dict[int, int] = {}

    for (cell_x, cell_z), cell_nodes in cells.items():
        for neighbor_x in (cell_x - 1, cell_x, cell_x + 1):
            for neighbor_z in (cell_z - 1, cell_z, cell_z + 1):
                for other in cells.get((neighbor_x, neighbor_z), ()):
                    for node in cell_nodes:
                        if node.node_id < other.node_id and (
                            math.dist((node.x, node.y, node.z), (other.x, other.y, other.z))
                            <= tolerance
                        ):
                            _union(parents, node.node_id, other.node_id)

    groups = defaultdict(list)

    for node_id in parents:
        groups[_root(parents, node_id)].append(node_id)

    return sorted(sorted(group) for group in groups.values())


def find_nodes_outside_map(autodrive_data: AutoDriveData, map_scale: int) -> list[int]:
    half_size = HeightmapTransform.calculate_world_size(map_scale) / 2

    return sorted(
        node.node_id
        for node in autodrive_data.nodes.values()
        if abs(node.x) > half_size or abs(node.z) > half_size
    )


def find_height_problems(
    autodrive_data: AutoDriveData,
    terrain_height_at: TerrainHeightProvider,
    max_difference: float,
) -> list[HeightProblem]:
    """Nodes whose height differs from the terrain by more than
    max_difference. Nodes without a terrain height (outside the map) are
    left out."""

    problems = []

    for node in autodrive_data.get_sorted_nodes():
        terrain_height = terrain_height_at(node.x, node.z)

        if terrain_height is not None and abs(node.y - terrain_height) > max_difference:
            problems.append(HeightProblem(node.node_id, node.y, terrain_height))

    return problems


def _root(parents: dict[int, int], node_id: int) -> int:
    while parents[node_id] != node_id:
        parents[node_id] = parents[parents[node_id]]
        node_id = parents[node_id]

    return node_id


def _union(parents: dict[int, int], first_id: int, second_id: int):
    parents.setdefault(first_id, first_id)
    parents.setdefault(second_id, second_id)
    parents[_root(parents, second_id)] = _root(parents, first_id)
