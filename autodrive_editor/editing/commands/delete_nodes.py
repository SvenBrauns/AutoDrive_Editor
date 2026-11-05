import dataclasses

from autodrive_editor.editing.commands.edit_command import DataChange, EditCommand
from autodrive_editor.i18n import tr
from autodrive_editor.model.autodrive_data import AutoDriveData, MarkerData, NodeData
from autodrive_editor.model.connections import (
    NO_CONNECTION,
    ConnectionState,
    write_connection_state,
)


class DeleteNodesCommand(EditCommand):
    """Deletes nodes together with their markers and all references
    to them in other nodes' connections.

    Node ids are not renumbered, so the data may contain gaps. They
    are closed when the AutoDrive XML is written.
    """

    def __init__(self, autodrive_data: AutoDriveData, node_ids):
        node_ids = frozenset(int(node_id) for node_id in node_ids)

        super().__init__(
            tr("Delete node")
            if len(node_ids) == 1
            else tr("Delete {count} nodes", count=len(node_ids)),
            autodrive_data,
        )

        if not node_ids:
            raise ValueError("No nodes to delete were given.")

        for node_id in node_ids:
            if node_id not in autodrive_data.nodes:
                raise ValueError(f"Node ID {node_id} does not exist.")

        self.node_ids = node_ids

        self._deleted_nodes: list[NodeData] = []
        self._deleted_markers: list[tuple[int, MarkerData]] = []

        # (neighbor id, "incoming" or "outgoing", deleted node id)
        self._removed_references: list[tuple[int, str, int]] = []

    def apply(self) -> DataChange:
        nodes = self.autodrive_data.nodes
        markers = self.autodrive_data.markers

        self._deleted_nodes = [nodes[node_id] for node_id in sorted(self.node_ids)]

        # Remember where each marker was, so undo puts it back in place.
        self._deleted_markers = [
            (position, marker)
            for position, marker in enumerate(markers.values())
            if marker.node_id in self.node_ids
        ]

        # Reverse connections are only stored in the source node's
        # outgoing set, so every node has to be checked.
        self._removed_references = []

        for node in nodes.values():
            if node.node_id in self.node_ids:
                continue

            for attribute in ("incoming", "outgoing"):
                connections = getattr(node, attribute)

                for deleted_id in connections & self.node_ids:
                    connections.discard(deleted_id)

                    self._removed_references.append((node.node_id, attribute, deleted_id))

        for node_id in self.node_ids:
            del nodes[node_id]
            markers.pop(node_id, None)

        return DataChange(removed_node_ids=self.node_ids, connection_node_ids=self._neighbor_ids())

    def revert(self) -> DataChange:
        for node in self._deleted_nodes:
            self.autodrive_data.add_node(node)

        for position, marker in self._deleted_markers:
            self.autodrive_data.add_marker(marker, position)

        for neighbor_id, attribute, deleted_id in self._removed_references:
            getattr(self.autodrive_data.nodes[neighbor_id], attribute).add(deleted_id)

        return DataChange(added_node_ids=self.node_ids, connection_node_ids=self._neighbor_ids())

    def _neighbor_ids(self) -> frozenset[int]:
        return frozenset(neighbor_id for neighbor_id, _, _ in self._removed_references)


class DeleteAndReconnectCommand(DeleteNodesCommand):
    """Deletes nodes and connects the kept nodes around them, so the road stays connected.
    The new connections come from road_edits.plan_reconnect() and did not exist before."""

    def __init__(
        self,
        autodrive_data: AutoDriveData,
        node_ids,
        connections: list[tuple[int, int, ConnectionState]],
    ):
        super().__init__(autodrive_data, node_ids)

        self.setText(
            tr("Delete and reconnect node")
            if len(self.node_ids) == 1
            else tr("Delete and reconnect {count} nodes", count=len(self.node_ids))
        )
        self.connections = list(connections)

    def apply(self) -> DataChange:
        change = super().apply()

        for source, target, state in self.connections:
            write_connection_state(self.autodrive_data, source, target, state)

        return self._with_ends(change)

    def revert(self) -> DataChange:
        for source, target, _ in self.connections:
            write_connection_state(self.autodrive_data, source, target, NO_CONNECTION)

        return self._with_ends(super().revert())

    def _with_ends(self, change: DataChange) -> DataChange:
        ends = frozenset(
            node_id for source, target, _ in self.connections for node_id in (source, target)
        )

        return dataclasses.replace(change, connection_node_ids=change.connection_node_ids | ends)
