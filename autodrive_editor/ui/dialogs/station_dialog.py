from PySide6.QtCore import Qt, QTimer, Signal
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

from autodrive_editor.editing.station_join import StopJoin, plan_direct, preview_piece
from autodrive_editor.editing.station_layout import (
    StationSettings,
    StopChoice,
    direction,
    lane_points,
    marker_names,
    occupied,
    plan_stations,
)
from autodrive_editor.file_io.navigation_costmap import NavigationCostmap
from autodrive_editor.file_io.savegame_stations import Stop
from autodrive_editor.i18n import tr
from autodrive_editor.model.autodrive_data import AutoDriveData
from autodrive_editor.settings.app_settings import AppSettings
from autodrive_editor.ui.dialogs.generator_settings_widget import GeneratorSettingsDialog

STOP, KIND, FILL_TYPES, NAME, GROUP, ANGLE, NOTE = range(7)
# Fill types listed in the table before "…".
SHOWN_FILL_TYPES = 3
# Least distance of a lane's handle on the map from its stop, in metres.
HANDLE_DISTANCE = 5.0
# The legs to the road are planned again this long after the last change, in milliseconds.
LEGS_DELAY = 200


class StationDialog(QDialog):
    """The picked stops with a check box each, their markers and lane angles;
    the lane lengths come from the generator settings.
    The planned lanes are sent with plan_changed, as for the parking spots, so the map can show
    them; the angles can also be set by dragging the lane ends on the map (handles). Shortly
    after a change the legs to the road that fit as curves are added (see station_join); the
    others are noted and searched on Create."""

    # (PlannedPiece or None, map points (x, z) of its nodes)
    plan_changed = Signal(object, object)

    def __init__(
        self,
        stops: list[Stop],
        headings: list[float],
        taken_names: set[tuple[str, str]],
        autodrive_data: AutoDriveData,
        app_settings: AppSettings,
        costmap: NavigationCostmap | None = None,
        parent=None,
    ):
        super().__init__(parent)

        self.setWindowTitle(tr("Create station lanes"))

        self.stops = list(stops)
        self.taken_names = set(taken_names)
        self.autodrive_data = autodrive_data
        self.nodes = list(autodrive_data.nodes.values())
        self.app_settings = app_settings
        self.costmap = costmap
        # The planned legs of the chosen stops by row.
        self.joins: dict[int, StopJoin] = {}
        self._legs_timer = QTimer(self)
        self._legs_timer.setSingleShot(True)
        self._legs_timer.setInterval(LEGS_DELAY)
        self._legs_timer.timeout.connect(self.update_legs)

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
            self.angle_inputs.append(self._angle_input(headings[row]))
            self.table.setCellWidget(row, ANGLE, self.angle_inputs[-1])

        self.table.resizeColumnsToContents()

        self.search_label = QLabel(
            tr("Legs to the road that do not fit as curves are searched on Create."), self
        )
        self.search_label.setWordWrap(True)
        self.search_label.hide()
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
        layout.addWidget(self.search_label)
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

    def update_legs(self):
        """Plans the legs of the chosen stops as curves and shows them; runs shortly after a
        change."""

        self._legs_timer.stop()
        settings, chosen = self.settings, self._chosen()
        radius, vehicle = self.app_settings.curve_radius, self.app_settings.vehicle
        self.joins = {
            row: plan_direct(self.autodrive_data, choice, settings, radius, self.costmap, vehicle)
            for row, choice in chosen
        }
        self._update_notes()
        self.search_label.setVisible(any(join.missing for join in self.joins.values()))
        piece = preview_piece([c for _, c in chosen], list(self.joins.values()), settings)
        self.plan_changed.emit(piece, [(x, z) for x, _, z in piece.points])

    def _chosen(self) -> list[tuple[int, StopChoice]]:
        return [
            (
                row,
                StopChoice(
                    stop,
                    self.table.item(row, NAME).text().strip(),
                    self.table.item(row, GROUP).text().strip(),
                    self.angle_inputs[row].value(),
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

    def handles(self) -> list[tuple[int, float, float, float, float]]:
        """(row, handle x, z, stop x, z) of each chosen stop: the handle sits at the front end
        of its lane, at least HANDLE_DISTANCE from the stop, and turns the lane around the stop."""

        result = []
        settings = self.settings
        length = max(settings.marker + settings.after, HANDLE_DISTANCE)

        for row, stop in enumerate(self.stops):
            if self.table.item(row, STOP).checkState() != Qt.Checked:
                continue

            dx, dz = direction(self.angle_inputs[row].value())
            x, _, z = stop.position
            result.append((row, x + dx * length, z + dz * length, x, z))

        return result

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

    def _angle_input(self, heading: float) -> QSpinBox:
        spin_box = QSpinBox(self)
        spin_box.setRange(0, 359)
        spin_box.setWrapping(True)
        spin_box.setSuffix("°")
        spin_box.setValue(round(heading) % 360)
        spin_box.valueChanged.connect(self._update)
        return spin_box

    def _update(self):
        self.joins = {}
        self._update_notes()
        settings = self.settings
        choices = self.choices
        problem = self._problem(choices)
        self.problem_label.setText(problem or "")
        self.create_button.setEnabled(problem is None)

        piece = plan_stations(choices, settings)
        self.plan_changed.emit(piece, [(x, z) for x, _, z in piece.points])
        self._legs_timer.start()

    def _update_notes(self):
        settings = self.settings
        self.table.blockSignals(True)

        for row, stop in enumerate(self.stops):
            points, _ = lane_points(stop, settings, self.angle_inputs[row].value())
            notes = []

            if not stop.from_ai_node:
                notes.append(tr("no AI node"))

            if occupied(points, self.nodes):
                notes.append(tr("existing node on the lane"))

            if row in self.joins:
                notes += self.joins[row].missing

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
