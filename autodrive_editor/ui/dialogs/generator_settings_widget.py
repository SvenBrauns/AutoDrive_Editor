"""The Generators settings page: curve radius, node spacing, vehicle size, station lanes and the
names and groups of generated markers, also of the bunker silo lanes. Shown in the Settings
dialog and on its own from the generator dialogs."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHeaderView,
    QLabel,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from autodrive_editor.editing.parking.bunker_silo import pattern_problem as silo_pattern_problem
from autodrive_editor.editing.parking.parking_layout import ParkingMode
from autodrive_editor.editing.routes.route_finder import Vehicle
from autodrive_editor.editing.stations.station_layout import (
    MarkerRule,
    StationSettings,
    pattern_problem,
)
from autodrive_editor.file_io.savegame_stations import StopKind
from autodrive_editor.i18n import tr
from autodrive_editor.settings.app_settings import AppSettings

KIND, PATTERN, GROUP = range(3)
SILO_MODES = {ParkingMode.BACK_IN: tr("Back in"), ParkingMode.DRIVE_THROUGH: tr("Drive through")}


class GeneratorSettingsWidget(QWidget):
    # Emitted when a value changes, so the dialog can check problem().
    changed = Signal()

    def __init__(self, settings: AppSettings, parent=None):
        super().__init__(parent)

        self.settings = settings
        vehicle = settings.vehicle
        stations = settings.station_settings

        self.curve_radius_input = self._metres_input(settings.curve_radius, 4.0, 50.0)
        self.spacing_input = self._metres_input(settings.generator_spacing, 1.0, 50.0)
        self.vehicle_width_input = self._metres_input(vehicle.width, 1.0, 10.0)
        self.safety_margin_input = self._metres_input(vehicle.margin, 0.1, 5.0)
        self.before_input = self._metres_input(stations.before, 0.0, 100.0)
        self.marker_input = self._metres_input(stations.marker, 0.0, 100.0)
        self.after_input = self._metres_input(stations.after, 0.0, 100.0)

        roads = QGroupBox(tr("Roads"), self)
        roads_note = QLabel(
            tr(
                "Find route, Junction and the generators build curves as arcs of the curve "
                "radius. Nodes lie at most the spacing apart on straights and closer in curves, "
                "as AutoDrive records them."
            ),
            roads,
        )
        roads_note.setWordWrap(True)
        roads_form = QFormLayout(roads)
        roads_form.addRow(roads_note)
        roads_form.addRow(tr("Curve radius:"), self.curve_radius_input)
        roads_form.addRow(tr("Spacing on straights:"), self.spacing_input)

        vehicle_box = QGroupBox(tr("Vehicle"), self)
        vehicle_note = QLabel(
            tr(
                "Routes keep half the vehicle width plus the safety margin away from buildings, "
                "fences and trees."
            ),
            vehicle_box,
        )
        vehicle_note.setWordWrap(True)
        vehicle_form = QFormLayout(vehicle_box)
        vehicle_form.addRow(vehicle_note)
        vehicle_form.addRow(tr("Vehicle width:"), self.vehicle_width_input)
        vehicle_form.addRow(tr("Safety margin:"), self.safety_margin_input)

        stations_box = QGroupBox(tr("Stations"), self)
        stations_form = QFormLayout(stations_box)
        stations_form.addRow(tr("Lane before the stop:"), self.before_input)
        stations_form.addRow(tr("Marker past the stop:"), self.marker_input)
        stations_form.addRow(tr("Lane after the marker:"), self.after_input)

        markers = QGroupBox(tr("Markers"), self)
        markers_note = QLabel(
            tr(
                "Placeholders: {building} the building's name, {type} the stop type, {fill} its "
                "first fill type, {action} unload or load, {n} a number counted per group "
                "({n:03} with three digits). Groups may use them too, except {n}."
            ),
            markers,
        )
        markers_note.setWordWrap(True)

        rules = settings.marker_rules
        self.rules_table = QTableWidget(len(StopKind), 3, markers)
        self.rules_table.setHorizontalHeaderLabels([tr("Stop type"), tr("Name"), tr("Group")])
        self.rules_table.verticalHeader().hide()
        self.rules_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        for row, kind in enumerate(StopKind):
            self._set_item(row, KIND, kind.label, editable=False)
            self._set_item(row, PATTERN, rules[kind].pattern)
            self._set_item(row, GROUP, rules[kind].group)

        self.rules_table.resizeRowsToContents()
        height = self.rules_table.horizontalHeader().height() + 2 * self.rules_table.frameWidth()
        height += sum(self.rules_table.rowHeight(row) for row in range(len(StopKind)))
        self.rules_table.setFixedHeight(height)

        silos = QGroupBox(tr("Bunker silos"), self)
        silos_note = QLabel(
            tr(
                "Placeholders: {building} the building's name, {letter} the silo's letter when "
                "several are picked (A, B, …), {n} the lane's number."
            ),
            silos,
        )
        silos_note.setWordWrap(True)

        patterns = settings.silo_patterns
        self.silo_table = QTableWidget(len(SILO_MODES), 3, silos)
        self.silo_table.setHorizontalHeaderLabels([tr("Mode"), tr("Name"), tr("Group")])
        self.silo_table.verticalHeader().hide()
        self.silo_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        for row, (mode, label) in enumerate(SILO_MODES.items()):
            self._set_item(row, KIND, label, editable=False, table=self.silo_table)
            self._set_item(row, PATTERN, patterns[mode][0], table=self.silo_table)
            self._set_item(row, GROUP, patterns[mode][1], table=self.silo_table)

        self.silo_table.resizeRowsToContents()
        height = self.silo_table.horizontalHeader().height() + 2 * self.silo_table.frameWidth()
        height += sum(self.silo_table.rowHeight(row) for row in range(len(SILO_MODES)))
        self.silo_table.setFixedHeight(height)

        silos_form = QFormLayout(silos)
        silos_form.addRow(silos_note)
        silos_form.addRow(self.silo_table)

        self.start_input = QSpinBox(markers)
        self.start_input.setRange(0, 9999)
        self.start_input.setValue(settings.marker_start)

        self.problem_label = QLabel(markers)
        self.problem_label.setWordWrap(True)

        markers_form = QFormLayout(markers)
        markers_form.addRow(markers_note)
        markers_form.addRow(self.rules_table)
        markers_form.addRow(tr("Numbers start at:"), self.start_input)
        markers_form.addRow(self.problem_label)

        layout = QVBoxLayout(self)
        layout.addWidget(roads)
        layout.addWidget(vehicle_box)
        layout.addWidget(stations_box)
        layout.addWidget(markers)
        layout.addWidget(silos)
        layout.addStretch(1)

        self.rules_table.itemChanged.connect(self._update)
        self.silo_table.itemChanged.connect(self._update)
        self._update()

    @property
    def rules(self) -> dict[StopKind, MarkerRule]:
        return {
            kind: MarkerRule(
                self.rules_table.item(row, PATTERN).text().strip(),
                self.rules_table.item(row, GROUP).text().strip(),
            )
            for row, kind in enumerate(StopKind)
        }

    @property
    def silo_patterns(self) -> dict[ParkingMode, tuple[str, str]]:
        return {
            mode: tuple(self.silo_table.item(row, column).text().strip() for column in (1, 2))
            for row, mode in enumerate(SILO_MODES)
        }

    def problem(self) -> str | None:
        for kind, rule in self.rules.items():
            problem = pattern_problem(rule.pattern)

            if problem is None and not rule.group:
                problem = tr("Every stop type needs a group.")

            if problem is None:
                problem = pattern_problem(rule.group, group=True)

            if problem is not None:
                return f"{kind.label}: {problem}"

        for mode, (name, group) in self.silo_patterns.items():
            problem = silo_pattern_problem(name) or silo_pattern_problem(group, group=True)

            if problem is not None:
                return f"{tr('Bunker silos')}, {SILO_MODES[mode]}: {problem}"

        return None

    def store(self):
        self.settings.set_curve_radius(self.curve_radius_input.value())
        self.settings.set_generator_spacing(self.spacing_input.value())
        self.settings.set_vehicle(
            Vehicle(width=self.vehicle_width_input.value(), margin=self.safety_margin_input.value())
        )
        self.settings.set_station_settings(
            StationSettings(
                before=self.before_input.value(),
                after=self.after_input.value(),
                marker=self.marker_input.value(),
            )
        )
        self.settings.set_marker_rules(self.rules)
        self.settings.set_silo_patterns(self.silo_patterns)
        self.settings.set_marker_start(self.start_input.value())

    def _update(self):
        self.problem_label.setText(self.problem() or "")
        self.changed.emit()

    def _set_item(self, row: int, column: int, text: str, editable=True, table=None):
        item = QTableWidgetItem(text)
        flags = Qt.ItemIsEnabled | Qt.ItemIsSelectable

        if editable:
            flags |= Qt.ItemIsEditable

        item.setFlags(flags)
        (table or self.rules_table).setItem(row, column, item)

    def _metres_input(self, value: float, minimum: float, maximum: float) -> QDoubleSpinBox:
        spin_box = QDoubleSpinBox(self)
        spin_box.setRange(minimum, maximum)
        spin_box.setDecimals(1)
        spin_box.setSingleStep(0.5)
        spin_box.setSuffix(" m")
        spin_box.setValue(value)

        return spin_box


class GeneratorSettingsDialog(QDialog):
    """The Generators page on its own, opened from a generator's dialog."""

    def __init__(self, settings: AppSettings, parent=None):
        super().__init__(parent)

        self.setWindowTitle(tr("Generator settings"))
        self.page = GeneratorSettingsWidget(settings, self)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self.ok_button = buttons.button(QDialogButtonBox.StandardButton.Ok)
        self.page.changed.connect(lambda: self.ok_button.setEnabled(self.page.problem() is None))

        layout = QVBoxLayout(self)
        layout.addWidget(self.page)
        layout.addWidget(buttons)

    def accept(self):
        self.page.store()
        super().accept()
