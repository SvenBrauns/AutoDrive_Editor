from collections.abc import Callable

from PySide6.QtCore import QPoint

from autodrive_editor.editing.edit_context import EditContext, EditOperation
from autodrive_editor.editing.parking_layout import ParkingSettings, ShedFrame, plan_parking
from autodrive_editor.editing.planned_piece import push_piece
from autodrive_editor.file_io.savegame_sheds import IndoorArea
from autodrive_editor.i18n import tr
from autodrive_editor.model.autodrive_data import AutoDriveData

# Asks for the parking spots of a shed; None if cancelled.
SettingsRequest = Callable[[IndoorArea, AutoDriveData], ParkingSettings | None]


class ParkingSpotOperation(EditOperation):
    """Creates the parking spots of a clicked shed in one undo step."""

    def __init__(
        self,
        context: EditContext,
        shed_at: Callable[[QPoint], IndoorArea | None],
        ask_settings: SettingsRequest,
        parent=None,
    ):
        super().__init__(context, parent)

        self.shed_at = shed_at
        self.ask_settings = ask_settings

    def create_at(self, view_position: QPoint) -> bool:
        autodrive_data = self.autodrive_data_provider()

        if autodrive_data is None or self.edit_history.history_locked:
            return False

        area = self.shed_at(view_position)

        if area is None:
            return False

        settings = self.ask_settings(area, autodrive_data)

        return settings is not None and self.create(area, settings)

    def create(self, area: IndoorArea, settings: ParkingSettings) -> bool:
        frame = ShedFrame.from_area(area, settings.open_side)

        def to_map(a: float, d: float) -> tuple[float, float, float]:
            x, z = frame.to_map(a, d)
            return x, area.height, z

        piece = plan_parking(frame, settings).moved(to_map)
        node_ids = push_piece(
            self.edit_history, self.autodrive_data_provider(), piece, tr("Create parking spots")
        )

        if self.node_selection is not None:
            open_ends = [node_ids[index] for index in piece.open_ends]
            self.node_selection.replace(set(open_ends), open_ends[0])

        self.status_changed.emit(
            tr(
                "{count} parking spots created; the selected line ends still need to be "
                "connected to the network",
                count=len(piece.markers),
            )
        )

        return True
