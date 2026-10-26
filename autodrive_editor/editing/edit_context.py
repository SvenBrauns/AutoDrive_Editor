from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Signal

from autodrive_editor.editing.edit_history import EditHistory
from autodrive_editor.model.autodrive_data import AutoDriveData
from autodrive_editor.terrain.terrain_follower import TerrainHeightProvider

if TYPE_CHECKING:
    from autodrive_editor.selection.node_selection import NodeSelection
    from autodrive_editor.selection.selection_coordinator import SelectionCoordinator
    from autodrive_editor.ui.map_view.map_view import MapView


@dataclass(frozen=True)
class EditContext:
    """The parts of the editor that edit operations work with. Tests leave
    out what an operation does not use."""

    edit_history: EditHistory
    autodrive_data_provider: Callable[[], AutoDriveData | None]
    view: MapView | None = None
    selection_coordinator: SelectionCoordinator | None = None
    node_selection: NodeSelection | None = None
    terrain_height_at: TerrainHeightProvider | None = None
    # Grid snapping of a map position.
    snap_point: Callable[[float, float], tuple[float, float]] | None = None


class EditOperation(QObject):
    """Base class of the editing workflows. Each change goes through the
    edit history; messages for the status bar go through status_changed."""

    status_changed = Signal(str)

    def __init__(self, context: EditContext, parent=None):
        super().__init__(parent)

        self.context = context
        self.edit_history = context.edit_history
        self.autodrive_data_provider = context.autodrive_data_provider
        self.view = context.view
        self.selection_coordinator = context.selection_coordinator
        self.node_selection = context.node_selection
        self.terrain_height_at = context.terrain_height_at
        self.snap_point = context.snap_point
