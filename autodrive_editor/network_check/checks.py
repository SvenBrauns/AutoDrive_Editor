"""Checks that find problems in an AutoDrive network."""

import math
from collections import defaultdict
from dataclasses import dataclass, field

from autodrive_editor.model.autodrive_data import AutoDriveData, NodeData
from autodrive_editor.terrain.heightmap_transform import HeightmapTransform
from autodrive_editor.terrain.terrain_follower import TerrainHeightProvider

# The kinds of checks.
OVERLAP, OUTSIDE, HEIGHT = "overlap", "outside", "height"
REFERENCES, UNCONNECTED = "references", "unconnected"
ALL_CHECKS = (OVERLAP, OUTSIDE, HEIGHT, REFERENCES, UNCONNECTED)


@dataclass(frozen=True)
class HeightProblem:
    """A node whose height differs too much from the terrain."""

    node_id: int
    height: float
    terrain_height: float


@dataclass(frozen=True)
class ReferenceProblem:
    """The invalid connection entries of a node: entries pointing to an
    unknown node or to the node itself, and incoming entries without the
    matching outgoing entry on the other node."""

    node_id: int
    outgoing: tuple[int, ...]
    incoming: tuple[int, ...]


@dataclass(frozen=True)
class CheckResults:
    """Problems found by the network check. height_problems is None when
    no heightmap was loaded, so the heights were not checked."""

    overlapping_groups: list[list[int]]
    outside_node_ids: list[int]
    height_problems: list[HeightProblem] | None
    reference_problems: list[ReferenceProblem] = field(default_factory=list)
    unconnected_node_ids: list[int] = field(default_factory=list)

    @property
    def problem_count(self) -> int:
        return (
            len(self.overlapping_groups)
            + len(self.outside_node_ids)
            + len(self.height_problems or [])
            + len(self.reference_problems)
            + len(self.unconnected_node_ids)
        )

    def entries(self) -> list[tuple[str, object]]:
        """(kind, problem) of every problem: the node id list of an
        overlapping group, the node id outside the map or without
        connections, the HeightProblem or the ReferenceProblem."""

        return (
            [(OVERLAP, group) for group in self.overlapping_groups]
            + [(OUTSIDE, node_id) for node_id in self.outside_node_ids]
            + [(HEIGHT, problem) for problem in self.height_problems or []]
            + [(REFERENCES, problem) for problem in self.reference_problems]
            + [(UNCONNECTED, node_id) for node_id in self.unconnected_node_ids]
        )

    @classmethod
    def from_entries(cls, entries) -> "CheckResults":
        """Results of (kind, problem) entries; duplicates are left out."""

        problems = {kind: [] for kind in ALL_CHECKS}

        for kind, problem in entries:
            if problem not in problems[kind]:
                problems[kind].append(problem)

        return cls(*(problems[kind] for kind in ALL_CHECKS))


def problem_node_ids(kind: str, problem) -> list[int]:
    """The nodes of an entry from CheckResults.entries()."""

    if kind == OVERLAP:
        return list(problem)

    if kind in (OUTSIDE, UNCONNECTED):
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
        reference_problems=(
            find_reference_problems(autodrive_data) if REFERENCES in checks else []
        ),
        unconnected_node_ids=(
            find_unconnected_nodes(autodrive_data) if UNCONNECTED in checks else []
        ),
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


def invalid_references(
    autodrive_data: AutoDriveData, node: NodeData
) -> tuple[tuple[int, ...], tuple[int, ...]]:
    """The node's invalid outgoing and incoming entries, as in
    ReferenceProblem. An outgoing entry without the matching incoming entry
    is a reverse connection, so it is valid."""

    nodes = autodrive_data.nodes

    outgoing = tuple(
        sorted(target for target in node.outgoing if target == node.node_id or target not in nodes)
    )
    incoming = tuple(
        sorted(
            source
            for source in node.incoming
            if source == node.node_id
            or source not in nodes
            or node.node_id not in nodes[source].outgoing
        )
    )

    return outgoing, incoming


def find_reference_problems(autodrive_data: AutoDriveData) -> list[ReferenceProblem]:
    problems = []

    for node in autodrive_data.get_sorted_nodes():
        outgoing, incoming = invalid_references(autodrive_data, node)

        if outgoing or incoming:
            problems.append(ReferenceProblem(node.node_id, outgoing, incoming))

    return problems


def find_unconnected_nodes(autodrive_data: AutoDriveData) -> list[int]:
    return sorted(
        node.node_id
        for node in autodrive_data.nodes.values()
        if not node.incoming and not node.outgoing
    )


def _root(parents: dict[int, int], node_id: int) -> int:
    while parents[node_id] != node_id:
        parents[node_id] = parents[parents[node_id]]
        node_id = parents[node_id]

    return node_id


def _union(parents: dict[int, int], first_id: int, second_id: int):
    parents.setdefault(first_id, first_id)
    parents.setdefault(second_id, second_id)
    parents[_root(parents, second_id)] = _root(parents, first_id)
