from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from autodrive_editor.editing.parking_layout import ParkingNetwork
from autodrive_editor.editing.station_layout import (
    StationSettings,
    StopChoice,
    default_group,
    default_marker_name,
    lane_points,
    occupied,
    plan_stations,
    unique_name,
)
from autodrive_editor.file_io.savegame_stations import Stop
from autodrive_editor.i18n import tr
from autodrive_editor.model.autodrive_data import NodeData
from autodrive_editor.model.connections import ConnectionType
from autodrive_editor.settings.app_settings import AppSettings

STOP, KIND, FILL_TYPES, NAME, GROUP, TURN, NOTE = range(7)
# Fill types listed in the table before "…".
SHOWN_FILL_TYPES = 3


class StationDialog(QDialog):
    """The picked stops with a check box each, their markers and the lane settings. The planned
    lanes are sent with plan_changed, as for the parking spots, so the map can show them."""

    # (ParkingNetwork or None, map points (x, z) of its nodes)
    plan_changed = Signal(object, object)

    def __init__(
        self,
        stops: list[Stop],
        taken_names: set[tuple[str, str]],
        nodes: list[NodeData],
        app_settings: AppSettings,
        parent=None,
    ):
        super().__init__(parent)

        self.setWindowTitle(tr("Create station lanes"))

        self.stops = list(stops)
        self.taken_names = set(taken_names)
        self.nodes = list(nodes)
        self.app_settings = app_settings

        self.table = QTableWidget(len(self.stops), 7, self)
        self.table.setHorizontalHeaderLabels(
            [
                tr("Stop"),
                tr("Type"),
                tr("Fill types"),
                tr("Marker"),
                tr("Group"),
                tr("Turn"),
                tr("Note"),
            ]
        )
        self.table.verticalHeader().hide()
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)

        names = set(self.taken_names)

        for row, stop in enumerate(self.stops):
            group = default_group(stop.kind)
            name = unique_name(default_marker_name(stop), group, names)
            names.add((name, group))

            self._set_item(row, STOP, stop.name.strip(), checked=True)
            self._set_item(row, KIND, stop.kind.label)
            fill_types = ", ".join(stop.fill_types[:SHOWN_FILL_TYPES])
            more = "…" if len(stop.fill_types) > SHOWN_FILL_TYPES else ""
            self._set_item(row, FILL_TYPES, fill_types + more)
            self._set_item(row, NAME, name, editable=True)
            self._set_item(row, GROUP, group, editable=True)
            self._set_item(row, TURN, "", checked=False)
            self._set_item(row, NOTE, "")

        defaults = app_settings.station_settings
        self.before_input = self._length_input(defaults.before, 0.0)
        self.after_input = self._length_input(defaults.after, 0.0)
        self.spacing_input = self._length_input(defaults.spacing, 1.0)

        form = QFormLayout()
        form.addRow(tr("Lane before the stop:"), self.before_input)
        form.addRow(tr("Lane after the stop:"), self.after_input)
        form.addRow(tr("Node spacing:"), self.spacing_input)

        self.problem_label = QLabel(self)
        self.problem_label.setWordWrap(True)

        buttons = QDialogButtonBox(QDialogButtonBox.Cancel, self)
        self.create_button = buttons.addButton(tr("Create"), QDialogButtonBox.AcceptRole)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(self.table)
        layout.addLayout(form)
        layout.addWidget(self.problem_label)
        layout.addWidget(buttons)
        self.resize(820, 420)

        self.table.itemChanged.connect(self._update)
        self._update()

    @property
    def settings(self) -> StationSettings:
        return StationSettings(
            self.before_input.value(), self.after_input.value(), self.spacing_input.value()
        )

    @property
    def choices(self) -> list[StopChoice]:
        return [
            StopChoice(
                stop,
                self.table.item(row, NAME).text().strip(),
                self.table.item(row, GROUP).text().strip(),
                self.table.item(row, TURN).checkState() == Qt.Checked,
            )
            for row, stop in enumerate(self.stops)
            if self.table.item(row, STOP).checkState() == Qt.Checked
        ]

    @property
    def is_valid(self) -> bool:
        return self.create_button.isEnabled()

    def accept(self):
        self.app_settings.set_station_settings(self.settings)
        super().accept()

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

    def _length_input(self, value: float, minimum: float) -> QDoubleSpinBox:
        spin_box = QDoubleSpinBox(self)
        spin_box.setRange(minimum, 100.0)
        spin_box.setDecimals(1)
        spin_box.setSuffix(" m")
        spin_box.setValue(value)
        spin_box.valueChanged.connect(self._update)
        return spin_box

    def _update(self):
        settings = self.settings
        self.table.blockSignals(True)

        for row, stop in enumerate(self.stops):
            turned = self.table.item(row, TURN).checkState() == Qt.Checked
            points, _ = lane_points(stop, settings, turned)
            notes = []

            if not stop.from_ai_node:
                notes.append(tr("no AI node, direction from the building"))

            if occupied(points, self.nodes):
                notes.append(tr("existing node on the lane"))

            self.table.item(row, NOTE).setText(", ".join(notes))

        self.table.blockSignals(False)

        choices = self.choices
        problem = self._problem(choices)
        self.problem_label.setText(problem or "")
        self.create_button.setEnabled(problem is None)

        network = plan_stations(choices, settings)
        overlay = ParkingNetwork(
            connections=[
                (source, target, ConnectionType.REGULAR) for source, target in network.connections
            ],
            markers=[(index, name) for index, name, _ in network.markers],
        )
        self.plan_changed.emit(overlay, [(x, z) for x, _, z in network.points])

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
