import math
from enum import Enum

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHeaderView,
    QLabel,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from autodrive_editor.editing.station_layout import (
    LaneEnd,
    StationSettings,
    StopChoice,
    can_join,
    direction,
    lane_points,
    marker_names,
    occupied,
    plan_stations,
)
from autodrive_editor.file_io.savegame_stations import Stop
from autodrive_editor.i18n import tr
from autodrive_editor.model.autodrive_data import AutoDriveData
from autodrive_editor.settings.app_settings import AppSettings
from autodrive_editor.ui.dialogs.generator_settings_widget import GeneratorSettingsDialog

STOP, KIND, FILL_TYPES, NAME, GROUP, ANGLE, NOTE = range(7)
# Fill types listed in the table before "…".
SHOWN_FILL_TYPES = 3
# Least distance of a lane's turn handle on the map from its stop, in metres.
HANDLE_DISTANCE = 5.0
# Shift snaps the lane angle to multiples of this, in degrees.
SNAP_DEGREES = 15


class LaneHandle(Enum):
    """The turn handle at the marker and the handles at the lane's first and last node."""

    TURN = "turn"
    START = "start"
    END = "end"


class StationDialog(QDialog):
    """The picked stops with a check box each, their markers and lane angles;
    the lane lengths come from the generator settings.
    The planned lanes are sent with plan_changed, as for the parking spots, so the map can show
    them. On the map the marker's handle turns a lane, the handles at its ends bend it and join
    a node they are dropped on; turning straightens the lane again."""

    # (PlannedPiece or None, map points (x, z) of its nodes)
    plan_changed = Signal(object, object)

    def __init__(
        self,
        stops: list[Stop],
        headings: list[float],
        taken_names: set[tuple[str, str]],
        autodrive_data: AutoDriveData,
        app_settings: AppSettings,
        parent=None,
    ):
        super().__init__(parent)

        self.setWindowTitle(tr("Create station lanes"))

        self.stops = list(stops)
        self.taken_names = set(taken_names)
        self.autodrive_data = autodrive_data
        self.nodes = list(autodrive_data.nodes.values())
        self.app_settings = app_settings

        self.table = QTableWidget(len(self.stops), 7, self)
        self.table.setHorizontalHeaderLabels(
            [
                tr("Stop"),
                tr("Type"),
                tr("Fill types"),
                tr("Marker"),
                tr("Group"),
                tr("Angle"),
                tr("Note"),
            ]
        )
        self.table.verticalHeader().hide()
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.angle_inputs: list[QSpinBox] = []
        # The dragged start and end of each row's lane, None while straight.
        self.lane_ends: list[list[LaneEnd | None]] = [[None, None] for _ in self.stops]

        self.markers = self._default_markers()

        for row, (stop, (name, group)) in enumerate(zip(self.stops, self.markers, strict=True)):
            self._set_item(row, STOP, stop.name.strip(), checked=True)
            self._set_item(row, KIND, stop.kind.label)
            fill_types = ", ".join(stop.fill_types[:SHOWN_FILL_TYPES])
            more = "…" if len(stop.fill_types) > SHOWN_FILL_TYPES else ""
            self._set_item(row, FILL_TYPES, fill_types + more)
            self._set_item(row, NAME, name, editable=True)
            self._set_item(row, GROUP, group, editable=True)
            self._set_item(row, NOTE, "")
            self.angle_inputs.append(self._angle_input(row, headings[row]))
            self.table.setCellWidget(row, ANGLE, self.angle_inputs[-1])

        self.table.resizeColumnsToContents()

        self.problem_label = QLabel(self)
        self.problem_label.setWordWrap(True)

        buttons = QDialogButtonBox(QDialogButtonBox.Cancel, self)
        self.create_button = buttons.addButton(tr("Create"), QDialogButtonBox.AcceptRole)
        self.settings_button = buttons.addButton(
            tr("Generator settings…"), QDialogButtonBox.ResetRole
        )
        self.settings_button.clicked.connect(self._edit_settings)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(self.table)
        layout.addWidget(self.problem_label)
        layout.addWidget(buttons)
        self.setSizeGripEnabled(True)
        self.resize(860, 420)

        self.table.itemChanged.connect(self._update)
        self._update()

    @property
    def settings(self) -> StationSettings:
        return self.app_settings.station_settings

    @property
    def choices(self) -> list[StopChoice]:
        return [choice for _, choice in self._chosen()]

    def _chosen(self) -> list[tuple[int, StopChoice]]:
        return [
            (
                row,
                StopChoice(
                    stop,
                    self.table.item(row, NAME).text().strip(),
                    self.table.item(row, GROUP).text().strip(),
                    self.angle_inputs[row].value(),
                    *self.lane_ends[row],
                ),
            )
            for row, stop in enumerate(self.stops)
            if self.table.item(row, STOP).checkState() == Qt.Checked
        ]

    @property
    def is_valid(self) -> bool:
        return self.create_button.isEnabled()

    def set_heading(self, row: int, heading: float):
        self.angle_inputs[row].setValue(round(heading) % 360)

    def handles(self) -> list[tuple[int, LaneHandle, float, float]]:
        """(row, kind, x, z) of the handles of each chosen lane: at its first and last node and
        the turn handle at the marker, at least HANDLE_DISTANCE from the stop."""

        result = []

        for row, choice in self._chosen():
            points, marker_index = lane_points(
                choice.stop, self.settings, choice.heading, choice.start, choice.end
            )
            x, _, z = choice.stop.position
            turn_x, _, turn_z = points[marker_index]

            if math.dist((x, z), (turn_x, turn_z)) < HANDLE_DISTANCE:
                dx, dz = direction(choice.heading)
                turn_x, turn_z = x + dx * HANDLE_DISTANCE, z + dz * HANDLE_DISTANCE

            result += [
                (row, LaneHandle.START, points[0][0], points[0][2]),
                (row, LaneHandle.END, points[-1][0], points[-1][2]),
                (row, LaneHandle.TURN, turn_x, turn_z),
            ]

        return result

    def drag_handle(
        self,
        handle: tuple[int, LaneHandle, float, float],
        x: float,
        z: float,
        node_id: int | None = None,
        snap: bool = False,
    ):
        """Turns the lane towards (x, z) (snap: in 15° steps) or moves its end there, onto the
        node `node_id` if the lane may join it there."""

        row, kind = handle[:2]

        if kind == LaneHandle.TURN:
            stop_x, _, stop_z = self.stops[row].position

            if math.hypot(x - stop_x, z - stop_z) > 0:
                heading = math.degrees(math.atan2(x - stop_x, stop_z - z)) % 360
                self.set_heading(
                    row, round(heading / SNAP_DEGREES) * SNAP_DEGREES if snap else heading
                )

            return

        at_start = kind == LaneHandle.START

        if node_id is not None and can_join(self.autodrive_data, node_id, at_start):
            node = self.autodrive_data.nodes[node_id]
            lane_end = LaneEnd(node.x, node.z, node_id)
        else:
            lane_end = LaneEnd(x, z)

        self.lane_ends[row][0 if at_start else 1] = lane_end
        self._update()

    def reload_settings(self):
        """After the generator settings changed: new lanes, and new marker names for the rows
        whose name and group were not edited."""

        markers = self._default_markers()
        self.table.blockSignals(True)

        for row, (old, new) in enumerate(zip(self.markers, markers, strict=True)):
            if (self.table.item(row, NAME).text(), self.table.item(row, GROUP).text()) == old:
                self.table.item(row, NAME).setText(new[0])
                self.table.item(row, GROUP).setText(new[1])

        self.table.blockSignals(False)
        self.markers = markers
        self._update()

    def _edit_settings(self):
        if GeneratorSettingsDialog(self.app_settings, self).exec():
            self.reload_settings()

    def _default_markers(self) -> list[tuple[str, str]]:
        rules, start = self.app_settings.marker_rules, self.app_settings.marker_start

        return marker_names(self.stops, rules, self.taken_names, start)

    def _set_item(self, row: int, column: int, text: str, editable=False, checked=None):
        item = QTableWidgetItem(text)
        flags = Qt.ItemIsEnabled | Qt.ItemIsSelectable

        if editable:
            flags |= Qt.ItemIsEditable

        if checked is not None:
            flags |= Qt.ItemIsUserCheckable
            item.setCheckState(Qt.Checked if checked else Qt.Unchecked)

        item.setFlags(flags)
        self.table.setItem(row, column, item)

    def _angle_input(self, row: int, heading: float) -> QSpinBox:
        spin_box = QSpinBox(self)
        spin_box.setRange(0, 359)
        spin_box.setWrapping(True)
        spin_box.setSuffix("°")
        spin_box.setValue(round(heading) % 360)
        spin_box.valueChanged.connect(lambda: self._straighten(row))
        return spin_box

    def _straighten(self, row: int):
        self.lane_ends[row] = [None, None]
        self._update()

    def _update(self):
        self._update_notes()
        settings = self.settings
        choices = self.choices
        problem = self._problem(choices)
        self.problem_label.setText(problem or "")
        self.create_button.setEnabled(problem is None)

        piece = plan_stations(choices, settings)
        self.plan_changed.emit(piece, [(x, z) for x, _, z in piece.points])

    def _update_notes(self):
        settings = self.settings
        self.table.blockSignals(True)

        for row, stop in enumerate(self.stops):
            start, end = self.lane_ends[row]
            points, _ = lane_points(stop, settings, self.angle_inputs[row].value(), start, end)
            notes = []

            if not stop.from_ai_node:
                notes.append(tr("no AI node"))

            # A joined end sits on its node.
            points = points[int(start is not None and start.node_id is not None) :]
            points = points[: len(points) - int(end is not None and end.node_id is not None)]

            if points and occupied(points, self.nodes):
                notes.append(tr("existing node on the lane"))

            note = self.table.item(row, NOTE)
            note.setText(", ".join(notes))
            note.setToolTip(note.text())

        self.table.blockSignals(False)

    def _problem(self, choices: list[StopChoice]) -> str | None:
        if not choices:
            return tr("No stop is chosen.")

        names = set(self.taken_names)

        for choice in choices:
            if not choice.name or not choice.group:
                return tr("Every chosen stop needs a marker name and a group.")

            if (choice.name, choice.group) in names:
                return tr(
                    "The marker “{name}” is already in the group “{group}”.",
                    name=choice.name,
                    group=choice.group,
                )

            names.add((choice.name, choice.group))

        return None
