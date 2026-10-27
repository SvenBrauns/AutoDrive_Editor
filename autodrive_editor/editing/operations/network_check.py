from collections.abc import Callable

from autodrive_editor.editing.commands.merge_nodes import MergeNodesCommand
from autodrive_editor.editing.commands.move_nodes import MoveNodesCommand
from autodrive_editor.editing.edit_context import EditContext, EditOperation
from autodrive_editor.i18n import tr
from autodrive_editor.model.autodrive_data import AutoDriveData
from autodrive_editor.terrain.heightmap_transform import HeightmapTransform


def choose_kept_node(autodrive_data: AutoDriveData, node_ids) -> int | None:
    """The node a group of overlapping nodes is merged into: the one with a
    marker, otherwise the lowest id. None if several nodes have markers."""

    marked = [node_id for node_id in node_ids if node_id in autodrive_data.markers]

    if len(marked) > 1:
        return None

    return marked[0] if marked else min(node_ids)


def position_on_map(x: float, z: float, map_scale: int, margin: float) -> tuple[float, float]:
    """The nearest position at least margin inside the map border."""

    limit = HeightmapTransform.calculate_world_size(map_scale) / 2 - margin

    return max(-limit, min(x, limit)), max(-limit, min(z, limit))


class NetworkCheckOperation(EditOperation):
    """Fixes the problems found by the network check. Each kind of fix is
    one undo step. Nodes deleted since the check are skipped."""

    # Distance from the map border for nodes moved back onto the map.
    MAP_EDGE_MARGIN = 1.0

    def __init__(self, context: EditContext, map_scale: Callable[[], int], parent=None):
        super().__init__(context, parent)

        self.map_scale = map_scale

    def merge_overlapping(self, groups: list[list[int]]) -> bool:
        autodrive_data = self._editable_data()

        if autodrive_data is None:
            return False

        merges = {}
        skipped_count = 0

        for group in groups:
            node_ids = [node_id for node_id in group if node_id in autodrive_data.nodes]

            if len(node_ids) < 2:
                continue

            kept_id = choose_kept_node(autodrive_data, node_ids)

            if kept_id is None:
                skipped_count += 1
            else:
                merges[kept_id] = set(node_ids) - {kept_id}

        if merges:
            self.edit_history.push(MergeNodesCommand(autodrive_data, merges))

        messages = []

        if merges:
            messages.append(
                tr("Overlapping nodes merged")
                if len(merges) == 1
                else tr("{count} groups of overlapping nodes merged", count=len(merges))
            )

        if skipped_count:
            messages.append(
                tr("{count} skipped: several nodes of the group have a marker", count=skipped_count)
            )

        if messages:
            self.status_changed.emit(" – ".join(messages))

        return bool(merges)

    def move_onto_map(self, node_ids) -> bool:
        """Moves the nodes to the nearest position inside the map. With a
        heightmap, they get the terrain height there."""

        autodrive_data = self._editable_data()

        if autodrive_data is None:
            return False

        old_positions = {}
        new_positions = {}

        for node_id in node_ids:
            node = autodrive_data.get_node(node_id)

            if node is None:
                continue

            x, z = position_on_map(node.x, node.z, self.map_scale(), self.MAP_EDGE_MARGIN)

            if (x, z) == (node.x, node.z):
                continue

            height = self.terrain_height_at(x, z) if self.terrain_height_at else None

            old_positions[node_id] = (node.x, node.y, node.z)
            new_positions[node_id] = (x, node.y if height is None else height, z)

        if not new_positions:
            return False

        count = len(new_positions)

        self.edit_history.push(
            MoveNodesCommand(
                autodrive_data,
                old_positions,
                new_positions,
                text=tr("Move node onto the map")
                if count == 1
                else tr("Move {count} nodes onto the map", count=count),
            )
        )

        self.status_changed.emit(
            tr("Node moved onto the map")
            if count == 1
            else tr("{count} nodes moved onto the map", count=count)
        )

        return True

    def set_heights_from_terrain(self, node_ids) -> bool:
        autodrive_data = self._editable_data()

        if autodrive_data is None:
            return False

        old_positions = {}
        new_positions = {}

        for node_id in node_ids:
            node = autodrive_data.get_node(node_id)
            height = self.terrain_height_at(node.x, node.z) if node is not None else None

            if height is not None and height != node.y:
                old_positions[node_id] = (node.x, node.y, node.z)
                new_positions[node_id] = (node.x, height, node.z)

        if not new_positions:
            return False

        count = len(new_positions)

        self.edit_history.push(
            MoveNodesCommand(
                autodrive_data,
                old_positions,
                new_positions,
                text=tr("Set node height from the terrain")
                if count == 1
                else tr("Set {count} node heights from the terrain", count=count),
            )
        )

        self.status_changed.emit(
            tr("Node height set from the terrain")
            if count == 1
            else tr("{count} node heights set from the terrain", count=count)
        )

        return True

    def _editable_data(self) -> AutoDriveData | None:
        if self.edit_history.history_locked:
            return None

        return self.autodrive_data_provider()
