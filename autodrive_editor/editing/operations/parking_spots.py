from collections.abc import Callable

from autodrive_editor.editing.edit_context import EditContext, EditOperation
from autodrive_editor.editing.parking.parking_layout import ParkingSettings, plan_sheds
from autodrive_editor.editing.planned_piece import push_piece
from autodrive_editor.file_io.savegame_sheds import IndoorArea
from autodrive_editor.i18n import tr
from autodrive_editor.model.autodrive_data import AutoDriveData

# Asks for the parking spots of the picked sheds; None if cancelled.
SettingsRequest = Callable[[list[IndoorArea], AutoDriveData], ParkingSettings | None]

MIXED_TYPES_TEXT = tr("The sheds are of different types: pick sheds of one type")


class ParkingSpotOperation(EditOperation):
    """Creates the parking spots of picked sheds of one type in one undo step."""

    def __init__(self, context: EditContext, ask_settings: SettingsRequest, parent=None):
        super().__init__(context, parent)

        self.ask_settings = ask_settings

    def create_for(self, areas: list[IndoorArea]) -> bool:
        autodrive_data = self.autodrive_data_provider()

        if autodrive_data is None or self.edit_history.history_locked or not areas:
            return False

        if len({area.building_file for area in areas}) > 1:
            self.status_changed.emit(MIXED_TYPES_TEXT)
            return False

        settings = self.ask_settings(areas, autodrive_data)

        return settings is not None and self.create(areas, settings)

    def create(self, areas: list[IndoorArea], settings: ParkingSettings) -> bool:
        piece = plan_sheds(areas, settings)
        push_piece(
            self.edit_history, self.autodrive_data_provider(), piece, tr("Create parking spots")
        )

        self.status_changed.emit(
            tr(
                "{count} parking spots created; the line ends still need to be connected to the "
                "network",
                count=len(piece.markers),
            )
        )

        return True
