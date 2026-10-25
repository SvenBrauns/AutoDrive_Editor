from collections.abc import Callable

from PySide6.QtCore import QObject, Signal

from autodrive_editor.editing.clipboard import ClipboardContent, copy_nodes, nodes_for_paste
from autodrive_editor.editing.commands.paste_nodes import PasteNodesCommand
from autodrive_editor.editing.edit_history import EditHistory
from autodrive_editor.model.autodrive_data import AutoDriveData
from autodrive_editor.selection.node_selection import NodeSelection


class ClipboardOperation(QObject):
    """Copy, cut and paste of the selected nodes. The clipboard stays
    filled when other data is loaded, so nodes can be pasted into another
    route."""

    status_changed = Signal(str)

    def __init__(
        self,
        node_selection: NodeSelection,
        edit_history: EditHistory,
        autodrive_data_provider: Callable[[], AutoDriveData | None],
        delete_nodes: Callable[[set[int]], bool],
        paste_position: Callable[[], tuple[float, float]],
        terrain_height_at: Callable[[float, float], float | None] | None = None,
        parent=None,
    ):
        super().__init__(parent)

        self.node_selection = node_selection
        self.edit_history = edit_history
        self.autodrive_data_provider = autodrive_data_provider
        self.delete_nodes = delete_nodes
        self.paste_position = paste_position
        self.terrain_height_at = terrain_height_at

        self.content: ClipboardContent | None = None

    def copy(self) -> bool:
        content = self._copy_selection()

        if content is None:
            return False

        self.content = content
        self.status_changed.emit(f"{self._count_text(len(content.nodes))} kopiert")

        return True

    def cut(self) -> bool:
        if self.edit_history.history_locked:
            return False

        content = self._copy_selection()

        if content is None:
            return False

        self.content = content
        self.delete_nodes({node.node_id for node in content.nodes})
        self.status_changed.emit(f"{self._count_text(len(content.nodes))} ausgeschnitten")

        return True

    def paste(self, at_original_position: bool = False) -> bool:
        """Pastes centered on the paste position (the mouse), or at the
        copied coordinates. The pasted nodes become the selection."""

        autodrive_data = self.autodrive_data_provider()

        if autodrive_data is None or self.edit_history.history_locked:
            return False

        if self.content is None:
            self.status_changed.emit("Die Zwischenablage ist leer")
            return False

        if at_original_position:
            offset, height_at = (0.0, 0.0), None
        else:
            target_x, target_z = self.paste_position()
            center_x, center_z = self.content.center
            offset, height_at = (target_x - center_x, target_z - center_z), self.terrain_height_at

        nodes, markers = nodes_for_paste(self.content, autodrive_data, offset, height_at)

        self.edit_history.push(PasteNodesCommand(autodrive_data, nodes, markers))

        new_ids = {node.node_id for node in nodes}
        self.node_selection.replace(new_ids, min(new_ids))

        self.status_changed.emit(f"{self._count_text(len(nodes))} eingefügt")

        return True

    def _copy_selection(self) -> ClipboardContent | None:
        autodrive_data = self.autodrive_data_provider()

        if autodrive_data is None:
            return None

        content = copy_nodes(autodrive_data, self.node_selection.selected_node_ids)

        if not content.nodes:
            self.status_changed.emit("Keine Nodes ausgewählt")
            return None

        return content

    @staticmethod
    def _count_text(count: int) -> str:
        return "1 Node" if count == 1 else f"{count} Nodes"
