from collections.abc import Callable

from autodrive_editor.editing.edit_context import EditContext, EditOperation
from autodrive_editor.editing.station_layout import StationSettings, StopChoice, stations_command
from autodrive_editor.file_io.savegame_stations import Stop
from autodrive_editor.i18n import tr
from autodrive_editor.model.autodrive_data import AutoDriveData

# Asks which stops to build and how; None if cancelled.
ChoiceRequest = Callable[
    [list[Stop], AutoDriveData], tuple[list[StopChoice], StationSettings] | None
]


class StationOperation(EditOperation):
    """Creates the lanes and markers of picked station stops in one undo step."""

    def __init__(self, context: EditContext, ask_choices: ChoiceRequest, parent=None):
        super().__init__(context, parent)

        self.ask_choices = ask_choices

    def create_for(self, stops: list[Stop]) -> bool:
        autodrive_data = self.autodrive_data_provider()

        if autodrive_data is None or self.edit_history.history_locked or not stops:
            return False

        answer = self.ask_choices(stops, autodrive_data)

        return answer is not None and self.create(*answer)

    def create(self, choices: list[StopChoice], settings: StationSettings) -> bool:
        if not choices:
            return False

        self.edit_history.push(stations_command(self.autodrive_data_provider(), choices, settings))
        self.status_changed.emit(
            tr(
                "{count} station lanes created; their open ends still need to be connected to "
                "the network",
                count=len(choices),
            )
        )

        return True
