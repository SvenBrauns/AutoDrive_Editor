from dataclasses import replace

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox

from autodrive_editor.editing.bunker_silo import (
    BACK_WALL_TO_MARKER,
    MARKER_PAST_SILO,
    pattern_problem,
    plan_silos,
    silo_settings,
)
from autodrive_editor.editing.parking_layout import ParkingMode, ParkingSettings, rows
from autodrive_editor.file_io.navigation_costmap import NavigationCostmap
from autodrive_editor.file_io.savegame_sheds import IndoorArea
from autodrive_editor.i18n import tr
from autodrive_editor.settings.app_settings import AppSettings
from autodrive_editor.ui.dialogs.parking_spot_dialog import ParkingSpotDialog

# The default marker distance as shown: from the back wall, or past the silo.
MARKER_DISTANCES = {
    ParkingMode.BACK_IN: BACK_WALL_TO_MARKER,
    ParkingMode.DRIVE_THROUGH: MARKER_PAST_SILO,
}


class SiloDialog(ParkingSpotDialog):
    """The shed dialog for the lanes of one or more bunker silos: one layout for all, marker
    name and group as patterns with {building}, {letter} and {n}. The views show one silo, chosen
    by its letter; the map shows the whole plan."""

    # The planned lanes of all silos as a piece in map points, or None while they don't fit.
    silos_changed = Signal(object)

    MARKER_OUTSIDE_TEXT = tr("The marker must be inside the silo.")
    LINE_INSIDE_TEXT = tr("The entry line must be at least {distance} m outside the silo.")

    def __init__(
        self,
        areas: list[IndoorArea],
        costmap: NavigationCostmap | None,
        groups: list[str],
        taken_names: set[tuple[str, str]],
        app_settings: AppSettings,
        parent=None,
    ):
        # Read by the methods the shed dialog calls while it is set up.
        self.areas = list(areas)
        self.costmap = costmap
        self.patterns = app_settings.silo_patterns
        self.silo_plan = None
        self.mode = None

        super().__init__(areas[0], groups, taken_names, app_settings, parent)

        self.setWindowTitle(tr("Create silo lanes"))
        self.reset_button.setText(tr("Reset silo settings"))
        self.form.labelForField(self.bays_input).setText(tr("Number of lanes:"))
        self.form.labelForField(self.bay_width_label).setText(tr("Lane width:"))

        self.silo_input = QComboBox(self)
        self.form.insertRow(0, tr("Silo:"), self.silo_input)
        self.form.setRowVisible(self.silo_input, len(self.areas) > 1)
        self._fill_silos()

        self.side_input.currentIndexChanged.connect(self._fill_silos)
        self.silo_input.currentIndexChanged.connect(self._silo_chosen)
        self.mode_input.currentIndexChanged.connect(self._mode_changed)

        self._update()

    @property
    def settings(self) -> ParkingSettings:
        settings = replace(super().settings, positions=1, silo=True)

        if settings.mode == ParkingMode.DRIVE_THROUGH:
            # Shown as the distance of the marker past the silo.
            return replace(settings, back_offset=-settings.back_offset)

        return settings

    def reset_shed_settings(self):
        settings = silo_settings(self.areas[0], self.costmap)
        self.apply_template(settings)
        self.name_input.setText(self.patterns[settings.mode][0])
        self.group_input.setCurrentText(self.patterns[settings.mode][1])
        self.start_input.setValue(self.app_settings.marker_start)

    def apply_template(self, template: ParkingSettings):
        if template.mode == ParkingMode.DRIVE_THROUGH:
            template = replace(template, back_offset=-template.back_offset)

        super().apply_template(template)
        self.mode = template.mode

    def _mode_changed(self):
        """Swaps in the other mode's patterns and marker distance unless they were changed."""

        old, new = self.mode, self.mode_input.currentData()
        self.mode = new

        if old is None or old == new:
            return

        if (self.name_input.text(), self.group_input.currentText()) == self.patterns[old]:
            self.name_input.setText(self.patterns[new][0])
            self.group_input.setCurrentText(self.patterns[new][1])

        if abs(self.back_input.value() - MARKER_DISTANCES[old]) < 1e-6:
            self.back_input.setValue(MARKER_DISTANCES[new])

    def _fill_silos(self):
        """The silos with their letters, in the order they get them from the open side."""

        order = [area for row in rows(self.areas, self.side_input.currentData()) for area in row]
        self.silo_input.blockSignals(True)
        self.silo_input.clear()

        for index, area in enumerate(order):
            self.silo_input.addItem(f"{chr(ord('A') + index)} – {area.name}", area)

        self.silo_input.setCurrentIndex(order.index(self.area))
        self.silo_input.blockSignals(False)

    def _silo_chosen(self):
        self.area = self.silo_input.currentData()
        self._update()

    def _update(self):
        self.silo_plan = None
        super()._update()

        back_in = self.mode_input.currentData() == ParkingMode.BACK_IN
        self.back_label.setText(tr("Back wall:") if back_in else tr("Marker past the silo:"))
        self.form.setRowVisible(self.positions_input, False)
        self.form.setRowVisible(self.spacing_input, False)

        if self.silo_plan is not None:
            self.hint_label.setText(self._names_text())

        self.silos_changed.emit(self.silo_plan)

    def _names_problem(self, settings) -> str | None:
        problem = pattern_problem(settings.marker_name) or pattern_problem(
            settings.group, group=True
        )

        if problem is not None:
            return problem

        try:
            piece = plan_silos(self.areas, settings)
        except ValueError:
            return tr("The settings don't fit every silo.")

        names = [(name, group) for _, name, group in piece.markers]

        for index, (name, group) in enumerate(names):
            if (name, group) in names[:index]:
                return tr("Two lanes would get the name “{name}”: add {{n}}.", name=name)

            if (name, group) in self.taken_names:
                return tr("A marker in this group already has the name “{name}”.", name=name)

        self.silo_plan = piece
        return None

    def _names_text(self) -> str:
        """The markers of each group, first to last."""

        groups: dict[str, list[str]] = {}

        for _, name, group in self.silo_plan.markers:
            groups.setdefault(group, []).append(name)

        lines = []

        for group, names in groups.items():
            shown = names[0] if len(names) == 1 else f"{names[0]} … {names[-1]}"
            new = "" if group in self.groups else tr(" (new)")
            lines.append(f"{group}{new}: {shown}")

        return "\n".join(lines)
