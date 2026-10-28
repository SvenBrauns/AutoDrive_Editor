from collections.abc import Callable

from PySide6.QtCore import QPoint

from autodrive_editor.editing.commands.paste_nodes import PasteNodesCommand
from autodrive_editor.editing.edit_context import EditContext, EditOperation
from autodrive_editor.editing.parking_layout import ParkingSettings, ShedFrame, plan_parking
from autodrive_editor.file_io.savegame_sheds import IndoorArea
from autodrive_editor.i18n import tr
from autodrive_editor.model.autodrive_data import SUBPRIO_FLAG, AutoDriveData, MarkerData, NodeData
from autodrive_editor.model.connections import CONNECTION_STATES, write_connection_state

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
        autodrive_data = self.autodrive_data_provider()
        frame = ShedFrame.from_area(area, settings.open_side)
        network = plan_parking(frame, settings)

        # The new nodes get their connections in a data set of their own, then are added at once.
        first_id = max(autodrive_data.nodes, default=0) + 1
        new_data = AutoDriveData()

        for index, (a, d) in enumerate(network.points):
            x, z = frame.to_map(a, d)
            new_data.add_node(NodeData(first_id + index, x, area.height, z, SUBPRIO_FLAG))

        for source, target, connection_type in network.connections:
            write_connection_state(
                new_data, first_id + source, first_id + target, CONNECTION_STATES[connection_type]
            )

        markers = [
            MarkerData(first_id + index, name, settings.group) for index, name in network.markers
        ]

        self.edit_history.push(
            PasteNodesCommand(
                autodrive_data,
                list(new_data.nodes.values()),
                markers,
                text=tr("Create parking spots"),
            )
        )

        if self.node_selection is not None:
            open_ends = [first_id + index for index in network.open_ends]
            self.node_selection.replace(set(open_ends), open_ends[0])

        self.status_changed.emit(
            tr(
                "{count} parking spots created; the selected line ends still need to be "
                "connected to the network",
                count=len(markers),
            )
        )

        return True
