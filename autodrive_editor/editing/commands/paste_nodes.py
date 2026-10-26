from autodrive_editor.editing.commands.edit_command import DataChange, EditCommand
from autodrive_editor.editing.commands.markers import GroupCreation
from autodrive_editor.i18n import tr
from autodrive_editor.model.autodrive_data import AutoDriveData, MarkerData, NodeData


class PasteNodesCommand(EditCommand):
    """Adds pasted nodes with their connections among each other and
    their markers. Markers go to the end of the marker list; unknown
    groups are created."""

    def __init__(
        self, autodrive_data: AutoDriveData, nodes: list[NodeData], markers: list[MarkerData]
    ):
        super().__init__(
            tr("Paste node") if len(nodes) == 1 else tr("Paste {count} nodes", count=len(nodes)),
            autodrive_data,
        )

        if not nodes:
            raise ValueError("No nodes to paste were given.")

        node_ids = {node.node_id for node in nodes}

        if node_ids & set(autodrive_data.nodes):
            raise ValueError("Pasted nodes need new node IDs.")

        if any(marker.node_id not in node_ids for marker in markers):
            raise ValueError("A pasted marker does not belong to a pasted node.")

        self.nodes = list(nodes)
        self.markers = list(markers)
        self.node_ids = frozenset(node_ids)

        group_names = list(dict.fromkeys(marker.group for marker in markers))
        self._groups = [GroupCreation(autodrive_data, name) for name in group_names]

    def apply(self) -> DataChange:
        for node in self.nodes:
            self.autodrive_data.add_node(node)

        for marker in self.markers:
            self.autodrive_data.add_marker(marker)

        groups_changed = [group.apply() for group in self._groups]

        return self._change(any(groups_changed))

    def revert(self) -> DataChange:
        for marker in self.markers:
            self.autodrive_data.remove_marker(marker.node_id)

        for node in self.nodes:
            del self.autodrive_data.nodes[node.node_id]

        groups_changed = [group.revert() for group in reversed(self._groups)]

        return self._change(any(groups_changed), removed=True)

    def _change(self, groups_changed: bool, removed: bool = False) -> DataChange:
        marker_node_ids = frozenset(marker.node_id for marker in self.markers)

        if removed:
            return DataChange(
                removed_node_ids=self.node_ids,
                changed_marker_node_ids=marker_node_ids,
                marker_groups_changed=groups_changed,
            )

        return DataChange(
            added_node_ids=self.node_ids,
            changed_marker_node_ids=marker_node_ids,
            marker_groups_changed=groups_changed,
        )
