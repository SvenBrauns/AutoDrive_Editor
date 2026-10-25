from __future__ import annotations

from dataclasses import dataclass, field

# AutoDrive node flags.
REGULAR_FLAG = 0
SUBPRIO_FLAG = 1


@dataclass
class NodeData:
    """One AutoDrive waypoint. x and z are the map position, y the height. incoming and outgoing
    hold the ids of connected nodes.
    """

    node_id: int
    x: float
    y: float
    z: float
    flag: int = 0

    incoming: set[int] = field(default_factory=set)

    outgoing: set[int] = field(default_factory=set)

    @property
    def is_regular(self) -> bool:
        return self.flag == 0

    @property
    def is_subprio(self) -> bool:
        return self.flag != 0


@dataclass
class MarkerData:
    """A named destination attached to a node."""

    node_id: int
    name: str = ""
    group: str = ""


@dataclass
class AutoDriveData:
    """All nodes and markers of an AutoDrive network, by node id."""

    nodes: dict[int, NodeData] = field(default_factory=dict)

    markers: dict[int, MarkerData] = field(default_factory=dict)

    def add_node(self, node: NodeData) -> None:
        if node.node_id <= 0:
            raise ValueError("Eine Node-ID muss größer als 0 sein.")

        if node.node_id in self.nodes:
            raise ValueError(f"Die Node-ID {node.node_id} ist bereits vorhanden.")

        self.nodes[node.node_id] = node

    def add_marker(self, marker: MarkerData) -> None:
        if marker.node_id not in self.nodes:
            raise ValueError(f"Der Marker verweist auf die unbekannte Node-ID {marker.node_id}.")

        self.markers[marker.node_id] = marker

    def get_node(self, node_id: int) -> NodeData | None:
        return self.nodes.get(node_id)

    def get_marker(self, node_id: int) -> MarkerData | None:
        return self.markers.get(node_id)

    def get_sorted_nodes(self) -> list[NodeData]:
        return [self.nodes[node_id] for node_id in sorted(self.nodes)]

    def validate_connections(self) -> list[str]:
        errors = []

        for node in self.nodes.values():
            for target_id in node.outgoing:
                if target_id not in self.nodes:
                    errors.append(
                        f"Node {node.node_id} besitzt eine "
                        f"ausgehende Verbindung zur unbekannten "
                        f"Node {target_id}."
                    )

            for source_id in node.incoming:
                if source_id not in self.nodes:
                    errors.append(
                        f"Node {node.node_id} besitzt eine "
                        f"eingehende Verbindung von der unbekannten "
                        f"Node {source_id}."
                    )

        return errors

    def clear(self) -> None:
        self.nodes.clear()
        self.markers.clear()

    def __len__(self) -> int:
        return len(self.nodes)
