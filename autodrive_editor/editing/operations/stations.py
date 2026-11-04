from collections.abc import Callable

from autodrive_editor.editing.edit_context import EditContext, EditOperation
from autodrive_editor.editing.station_layout import StationSettings, StopChoice, stations_command
from autodrive_editor.editing.station_yard import YardPlan, yard_command
from autodrive_editor.file_io.savegame_stations import Stop
from autodrive_editor.i18n import tr
from autodrive_editor.model.autodrive_data import AutoDriveData

# A yard plan and the nodes its road's start and end join.
Yard = tuple[YardPlan, tuple[int | None, int | None]]
# Asks which stops to build and how: the stops with their own lane, the settings and the yard,
# if one was drawn; None if cancelled.
ChoiceRequest = Callable[
    [list[Stop], AutoDriveData], tuple[list[StopChoice], StationSettings, Yard | None] | None
]


class StationOperation(EditOperation):
    """Creates the lanes and markers of picked station stops, and the yard road with the stops
    on it, in one undo step."""

    def __init__(
        self,
        context: EditContext,
        ask_choices: ChoiceRequest,
        height_for_new_node: Callable[[AutoDriveData, float, float], float] = lambda *_: 0.0,
        parent=None,
    ):
        super().__init__(context, parent)

        self.ask_choices = ask_choices
        self.height_for_new_node = height_for_new_node

    def create_for(self, stops: list[Stop]) -> bool:
        autodrive_data = self.autodrive_data_provider()

        if autodrive_data is None or self.edit_history.history_locked or not stops:
            return False

        answer = self.ask_choices(stops, autodrive_data)

        return answer is not None and self.create(*answer)

    def create(
        self, choices: list[StopChoice], settings: StationSettings, yard: Yard | None = None
    ) -> bool:
        autodrive_data = self.autodrive_data_provider()

        if yard is not None:
            plan, joined = yard
            self.edit_history.push(
                yard_command(
                    autodrive_data, plan, joined, choices, settings, self.height_for_new_node
                )
            )
            self.status_changed.emit(
                tr(
                    "Yard road created with {count} station stops",
                    count=len(plan.piece.markers) + len(choices),
                )
            )
            return True

        if not choices:
            return False

        self.edit_history.push(stations_command(autodrive_data, choices, settings))
        self.status_changed.emit(
            tr(
                "{count} station lanes created; their open ends still need to be connected to "
                "the network",
                count=len(choices),
            )
        )

        return True
