from autodrive_editor.editing.commands.edit_command import DataChange, EditCommand
from autodrive_editor.i18n import tr
from autodrive_editor.model.autodrive_data import AutoDriveData


class RemoveReferencesCommand(EditCommand):
    """Removes single connection entries, e.g. ones pointing to unknown
    nodes, in one undo step. Each reference is (node id, "incoming" or
    "outgoing", referenced id)."""

    def __init__(self, autodrive_data: AutoDriveData, references):
        self.references = sorted(set(references))

        if not self.references:
            raise ValueError("No references were given.")

        for node_id, attribute, referenced_id in self.references:
            if referenced_id not in getattr(autodrive_data.nodes[node_id], attribute):
                raise ValueError(f"Node {node_id} has no {attribute} entry {referenced_id}.")

        super().__init__(
            tr("Remove invalid connection reference")
            if len(self.references) == 1
            else tr("Remove {count} invalid connection references", count=len(self.references)),
            autodrive_data,
        )

    def apply(self) -> DataChange:
        for node_id, attribute, referenced_id in self.references:
            getattr(self.autodrive_data.nodes[node_id], attribute).discard(referenced_id)

        return self._change()

    def revert(self) -> DataChange:
        for node_id, attribute, referenced_id in self.references:
            getattr(self.autodrive_data.nodes[node_id], attribute).add(referenced_id)

        return self._change()

    def _change(self) -> DataChange:
        return DataChange(
            connection_node_ids=frozenset(node_id for node_id, _, _ in self.references)
        )
