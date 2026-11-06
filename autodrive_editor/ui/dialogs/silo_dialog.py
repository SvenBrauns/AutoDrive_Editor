from dataclasses import replace

from autodrive_editor.editing.parking.bunker_silo import (
    BACK_WALL_TO_MARKER,
    MARKER_PAST_SILO,
    pattern_problem,
    plan_silos,
    silo_settings,
)
from autodrive_editor.editing.parking.parking_layout import ParkingMode, ParkingSettings
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

    AREA_TEXT = tr("Silo:")

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
        self.costmap = costmap
        self.patterns = app_settings.silo_patterns
        self.mode = None

        super().__init__(areas, groups, taken_names, app_settings, parent)

        self.setWindowTitle(tr("Create silo lanes"))
        self.reset_button.setText(tr("Reset silo settings"))
        self.form.labelForField(self.bays_input).setText(tr("Number of lanes:"))
        self.form.labelForField(self.bay_width_label).setText(tr("Lane width:"))

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

    def area_label(self, index: int, area: IndoorArea) -> str:
        return f"{chr(ord('A') + index)} – {area.name}"

    def _update(self):
        super()._update()

        back_in = self.mode_input.currentData() == ParkingMode.BACK_IN
        self.back_label.setText(tr("Back wall:") if back_in else tr("Marker past the silo:"))
        self.form.setRowVisible(self.positions_input, False)
        self.form.setRowVisible(self.spacing_input, False)

        if self.area_plan is not None:
            self.hint_label.setText(self._names_text())

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

        self.area_plan = piece
        return None

    def _names_text(self) -> str:
        """The markers of each group, first to last."""

        groups: dict[str, list[str]] = {}

        for _, name, group in self.area_plan.markers:
            groups.setdefault(group, []).append(name)

        lines = []

        for group, names in groups.items():
            shown = names[0] if len(names) == 1 else f"{names[0]} … {names[-1]}"
            new = "" if group in self.groups else tr(" (new)")
            lines.append(f"{group}{new}: {shown}")

        return "\n".join(lines)
