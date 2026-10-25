from autodrive.models import (
    AutoDriveData,
    MarkerData,
    NodeData
)

from editing.edit_command import (
    DataChange,
    EditCommand
)


class DeleteNodesCommand(EditCommand):
    """Deletes nodes together with their markers and all references
    to them in other nodes' connections.

    Node ids are not renumbered, so the data may contain gaps. They
    are closed when the AutoDrive XML is written.
    """

    def __init__(
        self,
        autodrive_data: AutoDriveData,
        node_ids
    ):
        node_ids = frozenset(
            int(node_id)
            for node_id in node_ids
        )

        super().__init__(
            "Node löschen"
            if len(node_ids) == 1
            else f"{len(node_ids)} Nodes löschen",
            autodrive_data
        )

        if not node_ids:
            raise ValueError(
                "Es wurden keine Nodes zum "
                "Löschen angegeben."
            )

        for node_id in node_ids:
            if node_id not in autodrive_data.nodes:
                raise ValueError(
                    f"Die Node-ID {node_id} "
                    f"ist nicht vorhanden."
                )

        self.node_ids = node_ids

        self._deleted_nodes: list[NodeData] = []
        self._deleted_markers: list[MarkerData] = []

        # (neighbor id, "incoming" or "outgoing", deleted node id)
        self._removed_references: list[
            tuple[int, str, int]
        ] = []

    def apply(self) -> DataChange:
        nodes = self.autodrive_data.nodes
        markers = self.autodrive_data.markers

        self._deleted_nodes = [
            nodes[node_id]
            for node_id in sorted(self.node_ids)
        ]

        self._deleted_markers = [
            markers[node_id]
            for node_id in sorted(self.node_ids)
            if node_id in markers
        ]

        # Reverse connections are only stored in the source node's
        # outgoing set, so every node has to be checked.
        self._removed_references = []

        for node in nodes.values():
            if node.node_id in self.node_ids:
                continue

            for attribute in ("incoming", "outgoing"):
                connections = getattr(
                    node,
                    attribute
                )

                for deleted_id in connections & self.node_ids:
                    connections.discard(
                        deleted_id
                    )

                    self._removed_references.append(
                        (
                            node.node_id,
                            attribute,
                            deleted_id
                        )
                    )

        for node_id in self.node_ids:
            del nodes[node_id]
            markers.pop(
                node_id,
                None
            )

        return DataChange(
            removed_node_ids=self.node_ids,
            connection_node_ids=self._neighbor_ids()
        )

    def revert(self) -> DataChange:
        for node in self._deleted_nodes:
            self.autodrive_data.add_node(
                node
            )

        for marker in self._deleted_markers:
            self.autodrive_data.add_marker(
                marker
            )

        for (
            neighbor_id,
            attribute,
            deleted_id
        ) in self._removed_references:
            getattr(
                self.autodrive_data.nodes[neighbor_id],
                attribute
            ).add(
                deleted_id
            )

        return DataChange(
            added_node_ids=self.node_ids,
            connection_node_ids=self._neighbor_ids()
        )

    def _neighbor_ids(self) -> frozenset[int]:
        return frozenset(
            neighbor_id
            for neighbor_id, _, _ in self._removed_references
        )
