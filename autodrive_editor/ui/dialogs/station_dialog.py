import math
from enum import Enum

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
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
from autodrive_editor.editing.station_yard import (
    StopShape,
    YardPlan,
    YardStop,
    default_shapes,
    joined_ends,
    plan_yard,
)
from autodrive_editor.editing.yard_road import YardRoad, yard_road
from autodrive_editor.file_io.savegame_stations import Stop
from autodrive_editor.i18n import tr
from autodrive_editor.model.autodrive_data import AutoDriveData
from autodrive_editor.settings.app_settings import AppSettings
from autodrive_editor.ui.dialogs.generator_settings_widget import GeneratorSettingsDialog

STOP, KIND, FILL_TYPES, NAME, GROUP, ANGLE, SHAPE, NOTE = range(8)
# Fill types listed in the table before "…".
SHOWN_FILL_TYPES = 3
# Least distance of a lane's turn handle on the map from its stop, in metres.
HANDLE_DISTANCE = 5.0
# Shift snaps the lane angle to multiples of this, in degrees.
SNAP_DEGREES = 15


class LaneHandle(Enum):
    """The turn handle at the marker, the handles at the lane's first and last node and the
    corners of the yard road."""

    TURN = "turn"
    START = "start"
    END = "end"
    CORNER = "corner"


class StationDialog(QDialog):
    """The picked stops with a check box each, their markers and lane angles;
    the lane lengths come from the generator settings.
    The planned lanes are sent with plan_changed, as for the parking spots, so the map can show
    them. On the map the marker's handle turns a lane, the handles at its ends bend it and join
    a node they are dropped on; turning straightens the lane again.
    A yard road drawn on the map corner by corner (see yard_road) takes the stops as Branch,
    Chain or Back-in bay (see station_yard); a stop it cannot take keeps its own lane."""

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

        self.table = QTableWidget(len(self.stops), 8, self)
        self.table.setHorizontalHeaderLabels(
            [
                tr("Stop"),
                tr("Type"),
                tr("Fill types"),
                tr("Marker"),
                tr("Group"),
                tr("Angle"),
                tr("Shape"),
                tr("Note"),
            ]
        )
        self.table.verticalHeader().hide()
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.angle_inputs: list[QSpinBox] = []
        # The dragged start and end of each row's lane, None while straight.
        self.lane_ends: list[list[LaneEnd | None]] = [[None, None] for _ in self.stops]
        self.shape_inputs: list[QComboBox] = []
        self.shape_edited = [False] * len(self.stops)
        # The yard road: its corners, the node each was put on, the corner a Loop closes at.
        self.corners: list[tuple[float, float]] = []
        self.corner_nodes: list[int | None] = []
        self.closes_at: int | None = None
        self.drawing = False
        # Set by _update: the yard plan with the nodes its ends join, the rows built as lanes.
        self._yard: tuple[YardPlan, tuple[int | None, int | None]] | None = None
        self._lane_rows: set[int] = set()

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
            self.shape_inputs.append(self._shape_input(row))
            self.table.setCellWidget(row, SHAPE, self.shape_inputs[-1])

        self.table.resizeColumnsToContents()

        self.problem_label = QLabel(self)
        self.problem_label.setWordWrap(True)

        self.draw_button = QPushButton(tr("Draw yard road"), self)
        self.remove_road_button = QPushButton(tr("Remove yard road"), self)
        road_buttons = QHBoxLayout()

        for button in (self.draw_button, self.remove_road_button):
            # Enter finishes the road instead of pressing the button again.
            button.setAutoDefault(False)
            road_buttons.addWidget(button)

        road_buttons.addStretch()
        self.draw_button.clicked.connect(self.start_drawing)
        self.remove_road_button.clicked.connect(self.remove_road)

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
        layout.addLayout(road_buttons)
        layout.addWidget(self.problem_label)
        layout.addWidget(buttons)
        self.setSizeGripEnabled(True)
        self.resize(960, 420)

        self.table.itemChanged.connect(self._update)
        self._update()

    @property
    def settings(self) -> StationSettings:
        return self.app_settings.station_settings

    @property
    def choices(self) -> list[StopChoice]:
        return [choice for _, choice in self._chosen()]

    @property
    def lane_choices(self) -> list[StopChoice]:
        """The chosen stops built with their own lane."""

        return [choice for row, choice in self._chosen() if row in self._lane_rows]

    @property
    def yard(self) -> tuple[YardPlan, tuple[int | None, int | None]] | None:
        """The yard plan and the nodes its road's start and end join; None without a road."""

        return self._yard

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

            if row in self._lane_rows:
                result += [
                    (row, LaneHandle.START, points[0][0], points[0][2]),
                    (row, LaneHandle.END, points[-1][0], points[-1][2]),
                ]

            result.append((row, LaneHandle.TURN, turn_x, turn_z))

        corners = [(index, LaneHandle.CORNER, x, z) for index, (x, z) in enumerate(self.corners)]

        return result + corners

    def drag_handle(
        self,
        handle: tuple[int, LaneHandle, float, float],
        x: float,
        z: float,
        node_id: int | None = None,
        snap: bool = False,
    ):
        """Turns the lane towards (x, z) (snap: in 15° steps) or moves its end or a yard road
        corner there, onto the node `node_id` if the lane may join it there."""

        row, kind = handle[:2]

        if kind == LaneHandle.CORNER:
            self.corners[row], self.corner_nodes[row] = self._corner(x, z, node_id), node_id
            self._update()
            return

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

    def start_drawing(self):
        self.corners, self.corner_nodes, self.closes_at = [], [], None
        self.drawing = True
        self._update()

    def remove_road(self):
        self.corners, self.corner_nodes, self.closes_at = [], [], None
        self.drawing = False
        self._update()

    def click(self, handle, x: float, z: float, node_id: int | None) -> bool:
        """While drawing: a new corner at (x, z), on the node if one is given; a click on an
        earlier corner closes a Loop there and finishes."""

        if not self.drawing:
            return False

        if handle is not None and handle[1] == LaneHandle.CORNER:
            # A ring needs three corners.
            if len(self.corners) - handle[0] >= 3:
                self.closes_at = handle[0]
                self.drawing = False
                self._update()

            return True

        self.corners.append(self._corner(x, z, node_id))
        self.corner_nodes.append(node_id)
        self._update()
        return True

    def remove_last(self) -> bool:
        if not (self.drawing and self.corners):
            return False

        self.corners.pop()
        self.corner_nodes.pop()
        self._update()
        return True

    def finish(self) -> bool:
        """Ends drawing a Through road; fewer than two corners are no road."""

        if not self.drawing:
            return False

        if len(self.corners) < 2:
            self.corners, self.corner_nodes = [], []

        self.drawing = False
        self._update()
        return True

    def keyPressEvent(self, event):
        if self.drawing and event.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Escape):
            self.finish()
            return

        super().keyPressEvent(event)

    def _corner(self, x: float, z: float, node_id: int | None) -> tuple[float, float]:
        if node_id is None:
            return x, z

        node = self.autodrive_data.nodes[node_id]
        return node.x, node.z

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

    def _shape_input(self, row: int) -> QComboBox:
        combo_box = QComboBox(self)

        for shape in StopShape:
            combo_box.addItem(shape.label, shape)

        combo_box.setCurrentIndex(combo_box.findData(StopShape.LANE))
        combo_box.setEnabled(False)
        combo_box.currentIndexChanged.connect(lambda: self._edit_shape(row))
        return combo_box

    def _edit_shape(self, row: int):
        self.shape_edited[row] = True
        self._update()

    def _straighten(self, row: int):
        self.lane_ends[row] = [None, None]
        self._update()

    def _update(self):
        settings = self.settings
        chosen = self._chosen()
        road, joined = self._road()
        self._set_shapes(chosen, road)
        plan, failed = None, {}

        if road is not None:
            attached = {
                row: YardStop(choice, self.shape_inputs[row].currentData())
                for row, choice in chosen
                if self.shape_inputs[row].currentData() != StopShape.LANE
            }
            plan = plan_yard(road, list(attached.values()), settings, self._radius)
            rows = {id(stop.choice): row for row, stop in attached.items()}
            failed = {rows[id(choice)]: reason for choice, reason in plan.problems}
            self._lane_rows = {row for row, _ in chosen if row not in attached or row in failed}
        else:
            self._lane_rows = {row for row, _ in chosen}

        self._yard = (plan, joined) if plan is not None else None
        self._update_notes(failed)

        problem = self._problem([choice for _, choice in chosen], road)
        self.problem_label.setText(problem or self._warning() or "")
        self.create_button.setEnabled(problem is None)
        self.draw_button.setText(tr("Redraw yard road") if self.corners else tr("Draw yard road"))
        self.remove_road_button.setEnabled(bool(self.corners) or self.drawing)

        piece = plan_stations(self.lane_choices, settings).moved(lambda x, _, z: (x, z))

        if plan is not None:
            piece.add_piece(plan.piece)

        self.plan_changed.emit(piece, piece.points)

    @property
    def _radius(self) -> float:
        return self.app_settings.curve_radius

    def _road(self) -> tuple[YardRoad | None, tuple[int | None, int | None]]:
        if len(self.corners) < 2:
            return None, (None, None)

        loop = self.closes_at is not None
        corners, joined = joined_ends(self.autodrive_data, self.corners, self.corner_nodes, loop)

        if loop:
            corners.append(corners[self.closes_at])

        return yard_road(corners, self._radius, self.closes_at), joined

    def _set_shapes(self, chosen: list[tuple[int, StopChoice]], road: YardRoad | None):
        """Without a road every stop is a Lane; with one the rows not changed by hand get the
        default shapes. Removing or redrawing the road forgets the changes."""

        if not self.corners:
            self.shape_edited = [False] * len(self.stops)

        if road is None:
            # Corners too close keep the shapes until the road fits again.
            shapes = {} if self.corners else dict.fromkeys(range(len(self.stops)), StopShape.LANE)
        else:
            defaults = default_shapes([choice.stop for _, choice in chosen], road)
            shapes = {
                row: shape
                for (row, _), shape in zip(chosen, defaults, strict=True)
                if not self.shape_edited[row]
            }

        for row, combo_box in enumerate(self.shape_inputs):
            combo_box.blockSignals(True)
            combo_box.setEnabled(road is not None)

            if row in shapes:
                combo_box.setCurrentIndex(combo_box.findData(shapes[row]))

            combo_box.blockSignals(False)

    def _warning(self) -> str | None:
        """An existing node where the yard plan puts a new one."""

        if self._yard is None:
            return None

        plan, joined = self._yard
        ends = {end for end, node_id in zip(plan.ends, joined, strict=True) if node_id is not None}
        points = [
            (x, 0.0, z) for index, (x, z) in enumerate(plan.piece.points) if index not in ends
        ]

        if points and occupied(points, self.nodes):
            return tr("An existing node lies where the yard road or its branches go.")

        return None

    def _update_notes(self, failed: dict[int, str]):
        """Per stop: no AI node, why the yard road cannot take it, an existing node on its own
        lane."""

        settings = self.settings
        self.table.blockSignals(True)

        for row, stop in enumerate(self.stops):
            start, end = self.lane_ends[row]
            points, _ = lane_points(stop, settings, self.angle_inputs[row].value(), start, end)
            notes = []

            if not stop.from_ai_node:
                notes.append(tr("no AI node"))

            if row in failed:
                notes.append(failed[row])

            # A joined end sits on its node.
            points = points[int(start is not None and start.node_id is not None) :]
            points = points[: len(points) - int(end is not None and end.node_id is not None)]
            on_yard = self._yard is not None and row not in self._lane_rows

            if points and not on_yard and occupied(points, self.nodes):
                notes.append(tr("existing node on the lane"))

            note = self.table.item(row, NOTE)
            note.setText(", ".join(notes))
            note.setToolTip(note.text())

        self.table.blockSignals(False)

    def _problem(self, choices: list[StopChoice], road: YardRoad | None) -> str | None:
        if self.drawing:
            return tr(
                "Click the corners of the yard road on the map, on a node to join it; "
                "right-click removes the last one. Enter finishes, a click on an earlier corner "
                "closes a loop."
            )

        if self.corners and road is None:
            return tr(
                "The corners of the yard road are too close together for the curve radius of "
                "{radius} m.",
                radius=f"{self._radius:g}",
            )

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
