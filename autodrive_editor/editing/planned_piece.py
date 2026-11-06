"""A planned piece of network: nodes, connections and markers that generators build before they
are added to the route in one undo step.

Points are in the planner's own coordinates (map (x, y, z), or a shed's (a, d)); moved() turns
them into map positions before the piece is pushed.
"""

from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field

from autodrive_editor.editing.commands.add_route import AddRouteCommand
from autodrive_editor.editing.commands.delete_nodes import DeleteNodesCommand
from autodrive_editor.editing.commands.paste_nodes import PasteNodesCommand
from autodrive_editor.editing.edit_history import EditHistory
from autodrive_editor.model.autodrive_data import REGULAR_FLAG, AutoDriveData, MarkerData, NodeData
from autodrive_editor.model.connections import (
    CONNECTION_STATES,
    NO_CONNECTION,
    ConnectionType,
    read_connection_state,
    write_connection_state,
)


@dataclass
class PlannedPiece:
    """Nodes as points with a flag each, connections between their indices with a type, markers
    as (index, name, group), and the nodes that still need a connection to the network.
    Changes to the existing network: joins (index, node ID, out: the connection runs from the
    new node) with both directions of a pair becoming one two-way connection, directions
    (source ID, target ID) of existing connections to take away, and existing nodes to remove."""

    points: list[tuple[float, ...]] = field(default_factory=list)
    flags: list[int] = field(default_factory=list)
    connections: list[tuple[int, int, ConnectionType]] = field(default_factory=list)
    markers: list[tuple[int, str, str]] = field(default_factory=list)
    open_ends: list[int] = field(default_factory=list)
    joins: list[tuple[int, int, bool]] = field(default_factory=list)
    cut: list[tuple[int, int]] = field(default_factory=list)
    removed: set[int] = field(default_factory=set)

    def add(self, *point: float, flag: int = REGULAR_FLAG) -> int:
        self.points.append(point)
        self.flags.append(flag)

        return len(self.points) - 1

    def connect(self, source: int, target: int, connection_type=ConnectionType.REGULAR):
        self.connections.append((source, target, connection_type))

    def chain(self, indices: list[int], connection_type=ConnectionType.REGULAR):
        for source, target in zip(indices, indices[1:], strict=False):
            self.connect(source, target, connection_type)

    def add_piece(self, other: "PlannedPiece") -> int:
        """Adds the nodes, connections, markers and open ends of another piece; returns how far
        its node indices are shifted."""

        offset = len(self.points)
        self.points += other.points
        self.flags += other.flags
        self.connections += [(s + offset, t + offset, kind) for s, t, kind in other.connections]
        self.markers += [(index + offset, name, group) for index, name, group in other.markers]
        self.open_ends += [index + offset for index in other.open_ends]

        return offset

    def moved(self, to_map: Callable[..., tuple[float, float, float]]) -> "PlannedPiece":
        """The same piece with every point turned into a map position (x, y, z)."""

        return PlannedPiece(
            [to_map(*point) for point in self.points],
            list(self.flags),
            list(self.connections),
            list(self.markers),
            list(self.open_ends),
            list(self.joins),
            list(self.cut),
            set(self.removed),
        )


def push_piece(
    edit_history: EditHistory, autodrive_data: AutoDriveData, piece: PlannedPiece, text: str
) -> list[int]:
    """Adds the piece (points as map positions) to the route and returns the new node IDs by
    index: one PasteNodesCommand, or with changes to the existing network a DeleteNodesCommand
    for the removed nodes and one AddRouteCommand for the rest."""

    # The new nodes get their connections in a data set of their own, then are added at once.
    # Their IDs come after all existing ones, removed nodes included.
    first_id = max(autodrive_data.nodes, default=0) + 1
    node_ids = [first_id + index for index in range(len(piece.points))]
    if piece.removed:
        edit_history.push(DeleteNodesCommand(autodrive_data, piece.removed))
    new_data = AutoDriveData()

    for node_id, (x, y, z), flag in zip(node_ids, piece.points, piece.flags, strict=True):
        new_data.add_node(NodeData(node_id, x, y, z, flag))

    for source, target, connection_type in piece.connections:
        write_connection_state(
            new_data, node_ids[source], node_ids[target], CONNECTION_STATES[connection_type]
        )

    markers = [MarkerData(node_ids[index], name, group) for index, name, group in piece.markers]
    if not piece.joins and not piece.cut:
        edit_history.push(
            PasteNodesCommand(autodrive_data, list(new_data.nodes.values()), markers, text=text)
        )
        return node_ids

    states = [_without(autodrive_data, source, target) for source, target in piece.cut]
    directions = defaultdict(set)
    for index, node_id, out in piece.joins:
        directions[node_ids[index], node_id].add(out)
    for (new_id, node_id), outs in directions.items():
        kind = ConnectionType.DUAL if len(outs) == 2 else ConnectionType.REGULAR
        source, target = (new_id, node_id) if True in outs else (node_id, new_id)
        states.append((source, target, CONNECTION_STATES[kind]))
    edit_history.push(
        AddRouteCommand(text, autodrive_data, list(new_data.nodes.values()), states, markers)
    )

    return node_ids


def _without(autodrive_data: AutoDriveData, source: int, target: int):
    """The pair's connection state with the direction source → target taken away."""
    back = read_connection_state(autodrive_data, target, source)
    if back[0] and back[3]:  # target → source stays, one-way
        return source, target, (False, True, True, False)
    return source, target, NO_CONNECTION
