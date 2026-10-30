from collections.abc import Callable

from autodrive_editor.editing.commands.paste_nodes import PasteNodesCommand
from autodrive_editor.editing.edit_context import EditContext, EditOperation
from autodrive_editor.editing.station_layout import StationSettings, StopChoice, plan_stations
from autodrive_editor.file_io.savegame_stations import Stop
from autodrive_editor.i18n import tr
from autodrive_editor.model.autodrive_data import SUBPRIO_FLAG, AutoDriveData, MarkerData, NodeData
from autodrive_editor.model.connections import (
    CONNECTION_STATES,
    ConnectionType,
    write_connection_state,
)

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

        autodrive_data = self.autodrive_data_provider()
        network = plan_stations(choices, settings)

        # The new nodes get their connections in a data set of their own, then are added at once.
        first_id = max(autodrive_data.nodes, default=0) + 1
        new_data = AutoDriveData()

        for index, (x, y, z) in enumerate(network.points):
            new_data.add_node(NodeData(first_id + index, x, y, z, SUBPRIO_FLAG))

        regular = CONNECTION_STATES[ConnectionType.REGULAR]

        for source, target in network.connections:
            write_connection_state(new_data, first_id + source, first_id + target, regular)

        markers = [
            MarkerData(first_id + index, name, group) for index, name, group in network.markers
        ]

        self.edit_history.push(
            PasteNodesCommand(
                autodrive_data,
                list(new_data.nodes.values()),
                markers,
                text=tr("Create station lanes"),
            )
        )

        if self.node_selection is not None:
            open_ends = [first_id + index for index in network.open_ends]
            self.node_selection.replace(set(open_ends), open_ends[0])

        self.status_changed.emit(
            tr(
                "{count} station lanes created; the selected lane ends still need to be "
                "connected to the network",
                count=len(markers),
            )
        )

        return True
