from collections.abc import Callable

from autodrive_editor.editing.bunker_silo import plan_silos
from autodrive_editor.editing.edit_context import EditContext, EditOperation
from autodrive_editor.editing.parking_layout import ParkingSettings
from autodrive_editor.editing.planned_piece import push_piece
from autodrive_editor.file_io.savegame_sheds import IndoorArea
from autodrive_editor.i18n import tr
from autodrive_editor.model.autodrive_data import AutoDriveData

# Asks for the layout of the picked silos; None if cancelled.
SettingsRequest = Callable[[list[IndoorArea], AutoDriveData], ParkingSettings | None]


class BunkerSiloOperation(EditOperation):
    """Creates the lanes of picked bunker silos in one undo step."""

    def __init__(self, context: EditContext, ask_settings: SettingsRequest, parent=None):
        super().__init__(context, parent)

        self.ask_settings = ask_settings

    def create_for(self, areas: list[IndoorArea]) -> bool:
        autodrive_data = self.autodrive_data_provider()

        if autodrive_data is None or self.edit_history.history_locked or not areas:
            return False

        settings = self.ask_settings(areas, autodrive_data)

        return settings is not None and self.create(areas, settings)

    def create(self, areas: list[IndoorArea], settings: ParkingSettings) -> bool:
        piece = plan_silos(areas, settings)
        node_ids = push_piece(
            self.edit_history, self.autodrive_data_provider(), piece, tr("Create silo lanes")
        )

        if self.node_selection is not None and piece.open_ends:
            open_ends = [node_ids[index] for index in piece.open_ends]
            self.node_selection.replace(set(open_ends), open_ends[0])

        self.status_changed.emit(
            tr(
                "{count} silo lanes created; the selected line ends still need to be connected "
                "to the network",
                count=len(piece.markers),
            )
        )

        return True
