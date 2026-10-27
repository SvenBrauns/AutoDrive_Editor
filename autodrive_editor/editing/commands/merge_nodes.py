from autodrive_editor.editing.commands.edit_command import DataChange, EditCommand
from autodrive_editor.i18n import tr
from autodrive_editor.model.autodrive_data import AutoDriveData, NodeData


class MergeNodesCommand(EditCommand):
    """Merges groups of nodes into one kept node per group.

    The kept node takes over the connections of the other nodes of its
    group; connections between nodes of the same group are dropped. The
    other nodes are deleted and must not have a marker.
    """

    def __init__(self, autodrive_data: AutoDriveData, merges: dict[int, set[int]]):
        """merges maps each kept node id to the ids merged into it."""

        # Merged node id -> kept node id.
        self.replacements = {
            int(merged_id): int(kept_id)
            for kept_id, merged_ids in merges.items()
            for merged_id in merged_ids
            if int(merged_id) != int(kept_id)
        }

        self.kept_ids = frozenset(self.replacements.values())

        super().__init__(
            tr("Merge nodes")
            if len(self.kept_ids) == 1
            else tr("Merge {count} node groups", count=len(self.kept_ids)),
            autodrive_data,
        )

        if not self.replacements:
            raise ValueError("No nodes to merge were given.")

        if sum(len(set(ids) - {kept}) for kept, ids in merges.items()) != len(self.replacements):
            raise ValueError("A node can only be merged into one node.")

        if self.kept_ids & self.replacements.keys():
            raise ValueError("A kept node cannot be merged into another node.")

        for node_id in self.kept_ids | self.replacements.keys():
            if node_id not in autodrive_data.nodes:
                raise ValueError(f"Node ID {node_id} does not exist.")

        for node_id in self.replacements:
            if node_id in autodrive_data.markers:
                raise ValueError(f"Node {node_id} has a marker and cannot be merged away.")

        self._merged_nodes: list[NodeData] = []

        # Node id -> its incoming and outgoing sets before the merge.
        self._old_connections: dict[int, tuple[set[int], set[int]]] = {}

    def apply(self) -> DataChange:
        nodes = self.autodrive_data.nodes

        self._merged_nodes = [nodes[node_id] for node_id in sorted(self.replacements)]

        # Reverse connections are only stored in the source node's
        # outgoing set, so every node has to be checked.
        self._old_connections = {
            node.node_id: (node.incoming, node.outgoing)
            for node in nodes.values()
            if node.node_id not in self.replacements
            and (
                node.node_id in self.kept_ids
                or not self.replacements.keys().isdisjoint(node.incoming | node.outgoing)
            )
        }

        for node_id in self._old_connections:
            node = nodes[node_id]
            node.incoming = self._replace(node.incoming, node_id)
            node.outgoing = self._replace(node.outgoing, node_id)

        for merged in self._merged_nodes:
            kept = nodes[self.replacements[merged.node_id]]
            kept.incoming |= self._replace(merged.incoming, kept.node_id)
            kept.outgoing |= self._replace(merged.outgoing, kept.node_id)

        for node_id in self.replacements:
            del nodes[node_id]

        return DataChange(
            removed_node_ids=frozenset(self.replacements),
            connection_node_ids=frozenset(self._old_connections),
        )

    def revert(self) -> DataChange:
        for node in self._merged_nodes:
            self.autodrive_data.add_node(node)

        for node_id, (incoming, outgoing) in self._old_connections.items():
            node = self.autodrive_data.nodes[node_id]
            node.incoming = incoming
            node.outgoing = outgoing

        return DataChange(
            added_node_ids=frozenset(self.replacements),
            connection_node_ids=frozenset(self._old_connections),
        )

    def _replace(self, node_ids: set[int], own_id: int) -> set[int]:
        """The ids with merged nodes replaced by their kept node, without
        the node itself."""

        return {self.replacements.get(node_id, node_id) for node_id in node_ids} - {own_id}
