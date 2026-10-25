"""Copied nodes, kept inside the editor."""

import copy
from collections.abc import Callable
from dataclasses import dataclass

from autodrive_editor.model.autodrive_data import AutoDriveData, MarkerData, NodeData


@dataclass(frozen=True)
class ClipboardContent:
    """Copies of nodes with only the connections among each other, and
    their markers."""

    nodes: tuple[NodeData, ...]
    markers: tuple[MarkerData, ...]

    @property
    def center(self) -> tuple[float, float]:
        """Middle of the nodes' bounding box (x, z)."""

        xs = [node.x for node in self.nodes]
        zs = [node.z for node in self.nodes]

        return (min(xs) + max(xs)) / 2, (min(zs) + max(zs)) / 2


def copy_nodes(autodrive_data: AutoDriveData, node_ids) -> ClipboardContent:
    node_ids = {node_id for node_id in node_ids if node_id in autodrive_data.nodes}

    nodes = []

    for node_id in sorted(node_ids):
        node = copy.deepcopy(autodrive_data.nodes[node_id])
        node.outgoing &= node_ids
        node.incoming &= node_ids
        nodes.append(node)

    # In marker order, so pasted markers keep their order among each other.
    markers = [
        copy.deepcopy(marker)
        for node_id, marker in autodrive_data.markers.items()
        if node_id in node_ids
    ]

    return ClipboardContent(tuple(nodes), tuple(markers))


def nodes_for_paste(
    content: ClipboardContent,
    autodrive_data: AutoDriveData,
    offset: tuple[float, float],
    height_at: Callable[[float, float], float | None] | None = None,
) -> tuple[list[NodeData], list[MarkerData]]:
    """New nodes and markers for pasting the content shifted by offset.
    Nodes get new ids; marker names already used in their group get a
    number, e.g. "Tankstelle (2)". height_at gives the terrain height;
    without it (or outside the heightmap) the copied height stays."""

    next_id = max(autodrive_data.nodes, default=0) + 1
    new_ids = {node.node_id: next_id + index for index, node in enumerate(content.nodes)}

    dx, dz = offset
    nodes = []

    for original in content.nodes:
        x, z = original.x + dx, original.z + dz
        height = height_at(x, z) if height_at is not None else None

        nodes.append(
            NodeData(
                node_id=new_ids[original.node_id],
                x=x,
                y=original.y if height is None else height,
                z=z,
                flag=original.flag,
                outgoing={new_ids[node_id] for node_id in original.outgoing},
                incoming={new_ids[node_id] for node_id in original.incoming},
            )
        )

    taken = {(marker.name, marker.group) for marker in autodrive_data.markers.values()}
    markers = []

    for original in content.markers:
        name = _free_name(original.name, original.group, taken)
        taken.add((name, original.group))
        markers.append(MarkerData(new_ids[original.node_id], name, original.group))

    return nodes, markers


def _free_name(name: str, group: str, taken: set[tuple[str, str]]) -> str:
    if (name, group) not in taken:
        return name

    number = 2

    while (f"{name} ({number})", group) in taken:
        number += 1

    return f"{name} ({number})"
