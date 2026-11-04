from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QSpinBox,
    QVBoxLayout,
)

from autodrive_editor.editing.parking_layout import (
    ENTRY_LINE_OUTSIDE,
    MIN_BAY_WIDTH,
    BayLine,
    ParkingMode,
    ParkingSettings,
    ShedFrame,
    bay_line,
    bay_width,
    default_open_side,
    drive_through_line,
    from_template,
    marker_depth,
    plan_parking,
    plan_sheds,
    positions_fit,
    rows,
    side_angle,
    template_values,
)
from autodrive_editor.file_io.savegame_sheds import IndoorArea
from autodrive_editor.i18n import tr
from autodrive_editor.settings.app_settings import AppSettings
from autodrive_editor.ui.dialogs.bay_line_preview import BayLinePreview
from autodrive_editor.ui.dialogs.list_choice_dialog import ListChoiceDialog
from autodrive_editor.ui.dialogs.parking_preview import SIDE_NAMES, ParkingPreview, compass_name

# Bay width the default number of bays is based on (marker G1 of the example route).
DEFAULT_BAY_WIDTH = 6.6
DEFAULTS = ParkingSettings()


class ParkingSpotDialog(QDialog):
    """Asks how the parking spots of one or more sheds of one type are laid out and named, with
    a live top view. One layout for all; the views show one shed, chosen in the area list; the
    map shows the whole plan."""

    # The planned network of all areas as a piece in map points, or None while it doesn't fit.
    area_plan_changed = Signal(object)

    AREA_TEXT = tr("Shed:")

    EMPTY_NAME_TEXT = tr("Please enter a marker name.")
    EMPTY_GROUP_TEXT = tr("Please choose or enter a group.")
    MARKER_OUTSIDE_TEXT = tr("The marker must be inside the shed.")
    LINE_INSIDE_TEXT = tr("The entry line must be at least {distance} m outside the shed.")

    def __init__(
        self,
        areas: list[IndoorArea],
        groups: list[str],
        taken_names: set[tuple[str, str]],
        app_settings: AppSettings,
        parent=None,
    ):
        super().__init__(parent)

        self.setWindowTitle(tr("Create parking spots"))

        self.areas = list(areas)
        # The area the views show.
        self.area = self.areas[0]
        # Templates are kept per building type.
        self.template_file = self.area.building_file
        self.area_plan = None
        self.groups = list(groups)
        self.taken_names = set(taken_names)
        self.app_settings = app_settings

        self.mode_input = QComboBox(self)
        self.mode_input.addItem(tr("Back in"), ParkingMode.BACK_IN)
        self.mode_input.addItem(tr("Drive through"), ParkingMode.DRIVE_THROUGH)

        self.side_input = QComboBox(self)

        for side, name in SIDE_NAMES.items():
            compass = compass_name(side_angle(self.area, side))
            self.side_input.addItem(f"{name} ({compass})", side)

        self.bays_input = QSpinBox(self)
        self.bays_input.setRange(1, 99)
        self.bay_width_label = QLabel(self)

        self.left_input = self._length_input()
        self.right_input = self._length_input()
        self.back_input = self._length_input()
        self.gap_input = self._length_input()
        # Blank while the gaps differ.
        self.gap_input.setMinimum(-0.1)
        self.gap_input.setSpecialValueText(" ")

        self.positions_input = QSpinBox(self)
        self.positions_input.setRange(1, 20)
        self.spacing_input = self._length_input()
        self.spacing_input.setMinimum(1.0)

        self.entry_direction_input = self._direction_input()
        self.exit_direction_input = self._direction_input()

        self.name_input = QLineEdit(tr("Shed"), self)
        self.start_input = QSpinBox(self)
        self.start_input.setRange(0, 9999)
        self.start_input.setValue(1)

        self.group_input = QComboBox(self)
        self.group_input.setEditable(True)
        self.group_input.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.group_input.addItems(sorted(self.groups, key=str.casefold))
        self.group_input.setCurrentText("")

        self.gaps: list[float] = []
        # None fits the default bay line to the shed.
        self.bay_line: BayLine | None = None
        self.popup: LengthPopup | None = None

        self.preview = ParkingPreview(self)
        self.preview.side_clicked.connect(self._open_side)
        self.preview.length_clicked.connect(self._edit_shed_length)

        self.side_view = BayLinePreview(self)
        self.side_view.line_changed.connect(self._set_bay_line)
        self.side_view.length_clicked.connect(self._edit_segment)

        self.hint_label = QLabel(self)
        self.hint_label.setWordWrap(True)

        self.buttons = QDialogButtonBox(self)
        self.create_button = self.buttons.addButton(
            tr("Create"), QDialogButtonBox.ButtonRole.AcceptRole
        )
        self.buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
        self.reset_button = self.buttons.addButton(
            tr("Reset shed settings"), QDialogButtonBox.ButtonRole.ResetRole
        )
        self.load_button = self.buttons.addButton(
            tr("Load template…"), QDialogButtonBox.ButtonRole.ActionRole
        )
        self.save_button = self.buttons.addButton(
            tr("Save as template…"), QDialogButtonBox.ButtonRole.ActionRole
        )
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        self.reset_button.clicked.connect(self.reset_shed_settings)
        self.load_button.clicked.connect(self._load_clicked)
        self.save_button.clicked.connect(self._save_clicked)

        self.area_input = QComboBox(self)

        form = QFormLayout()
        form.addRow(self.AREA_TEXT, self.area_input)
        form.setRowVisible(self.area_input, len(self.areas) > 1)
        form.addRow(tr("Mode:"), self.mode_input)
        self.side_label = QLabel(self)
        form.addRow(self.side_label, self.side_input)
        form.addRow(tr("Number of bays:"), self.bays_input)
        form.addRow(tr("Bay width:"), self.bay_width_label)
        form.addRow(tr("Left wall:"), self.left_input)
        form.addRow(tr("Right wall:"), self.right_input)
        self.back_label = QLabel(self)
        form.addRow(self.back_label, self.back_input)
        form.addRow(tr("All gaps:"), self.gap_input)
        form.addRow(tr("Positions per bay:"), self.positions_input)
        form.addRow(tr("Position spacing:"), self.spacing_input)
        self.form = form
        form.addRow(tr("Entry line:"), self.entry_direction_input)
        form.addRow(tr("Exit line:"), self.exit_direction_input)
        form.addRow(tr("Marker name:"), self.name_input)
        form.addRow(tr("Start number:"), self.start_input)
        form.addRow(tr("Group:"), self.group_input)

        previews = QVBoxLayout()
        previews.addWidget(self.preview, 1)
        previews.addWidget(self.side_view)

        columns = QHBoxLayout()
        columns.addLayout(form)
        columns.addLayout(previews, 1)

        layout = QVBoxLayout(self)
        layout.addLayout(columns)
        layout.addWidget(self.hint_label)
        layout.addWidget(self.buttons)

        self.reset_shed_settings()
        last = self.app_settings.last_parking_template(self.template_file)

        if last in self.templates:
            self.apply_template(self.templates[last])

        self._update_load_button()

        for widget in (self.mode_input, self.side_input) + self._direction_inputs():
            widget.currentIndexChanged.connect(self._update)

        for widget in (
            self.start_input,
            self.left_input,
            self.right_input,
            self.back_input,
            self.positions_input,
            self.spacing_input,
        ):
            widget.valueChanged.connect(self._update)

        self.bays_input.valueChanged.connect(self._bays_changed)
        self.gap_input.valueChanged.connect(self._all_gaps_changed)

        self.name_input.textChanged.connect(self._update)
        self.group_input.currentTextChanged.connect(self._update)

        self._fill_areas()
        self.side_input.currentIndexChanged.connect(self._fill_areas)
        self.area_input.currentIndexChanged.connect(self._area_chosen)

        self._update()

    @property
    def settings(self) -> ParkingSettings:
        bays = self.bays_input.value()

        return ParkingSettings(
            mode=self.mode_input.currentData(),
            open_side=self.side_input.currentData(),
            bays=bays,
            left_offset=self.left_input.value(),
            right_offset=self.right_input.value(),
            back_offset=self.back_input.value(),
            gaps=tuple(self.gaps[: bays - 1]),
            entry_left_to_right=self.entry_direction_input.currentData(),
            exit_left_to_right=self.exit_direction_input.currentData(),
            bay_line=self.bay_line,
            positions=self.positions_input.value(),
            position_spacing=self.spacing_input.value(),
            marker_name=self.name_input.text().strip(),
            start_number=self.start_input.value(),
            group=self.group_input.currentText().strip(),
        )

    @property
    def is_valid(self) -> bool:
        return self.create_button.isEnabled()

    def reset_shed_settings(self):
        """Mode, open side, bays and offsets as for a shed type without a template."""

        side = default_open_side(self.area)
        length = ShedFrame.from_area(self.area, side).length

        self.mode_input.setCurrentIndex(self.mode_input.findData(DEFAULTS.mode))
        self.side_input.setCurrentIndex(self.side_input.findData(side))
        self.bays_input.setValue(max(1, int(length // DEFAULT_BAY_WIDTH)))
        self.left_input.setValue(DEFAULTS.left_offset)
        self.right_input.setValue(DEFAULTS.right_offset)
        self.back_input.setValue(DEFAULTS.back_offset)
        self.positions_input.setValue(DEFAULTS.positions)
        self.spacing_input.setValue(DEFAULTS.position_spacing)
        self.gap_input.setValue(0.0)
        self.gaps = [0.0] * (self.bays_input.value() - 1)
        self.bay_line = None
        self._update()

    @property
    def templates(self) -> dict[str, ParkingSettings]:
        """The readable templates of this shed type, by name."""

        templates = {}

        for name, values in self.app_settings.parking_templates(self.template_file).items():
            try:
                templates[name] = from_template(values)
            except ValueError:
                continue

        return templates

    def apply_template(self, template: ParkingSettings):
        self.mode_input.setCurrentIndex(self.mode_input.findData(template.mode))
        self.side_input.setCurrentIndex(self.side_input.findData(template.open_side))
        self.bays_input.setValue(template.bays)
        self.left_input.setValue(template.left_offset)
        self.right_input.setValue(template.right_offset)
        self.back_input.setValue(template.back_offset)
        self.positions_input.setValue(template.positions)
        self.spacing_input.setValue(template.position_spacing)
        self.gaps = list(template.gaps)
        self.bay_line = template.bay_line
        self._update()

    def load_template(self, name: str):
        self.apply_template(self.templates[name])
        self.app_settings.set_last_parking_template(self.template_file, name)

    def save_template(self, name: str):
        values = template_values(self.settings)
        self.app_settings.save_parking_template(self.template_file, name, values)
        self._update_load_button()

    def delete_template(self, name: str):
        self.app_settings.delete_parking_template(self.template_file, name)
        self._update_load_button()

    def _update_load_button(self):
        self.load_button.setEnabled(bool(self.templates))

    def _load_clicked(self):
        name = self._choose_template()

        if name is not None:
            self.load_template(name)

    def _save_clicked(self):
        name = self._ask_template_name()

        if name is not None and (name not in self.templates or self._confirm_replace(name)):
            self.save_template(name)

    def _choose_template(self) -> str | None:
        """Lists this shed type's templates; they can be deleted there."""

        rows = [
            ([name, self.mode_input.itemText(self.mode_input.findData(t.mode)), str(t.bays)], name)
            for name, t in self.templates.items()
        ]
        dialog = ListChoiceDialog(
            tr("Load template"),
            tr("Templates of {building}:", building=self.template_file),
            [tr("Name"), tr("Mode"), tr("Bays")],
            rows,
            ok_text=tr("Load"),
            parent=self,
        )
        delete_button = dialog.buttons.addButton(
            tr("Delete"), QDialogButtonBox.ButtonRole.ActionRole
        )

        def delete():
            item = dialog.table.currentItem()

            if item is not None and self._confirm_delete(dialog.chosen_value):
                self.delete_template(dialog.chosen_value)
                dialog.table.takeTopLevelItem(dialog.table.indexOfTopLevelItem(item))

        delete_button.clicked.connect(delete)
        dialog.table.itemSelectionChanged.connect(
            lambda: delete_button.setEnabled(dialog.table.currentItem() is not None)
        )

        return dialog.chosen_value if dialog.exec() else None

    def _ask_template_name(self) -> str | None:
        last = self.app_settings.last_parking_template(self.template_file) or ""
        name, accepted = QInputDialog.getText(
            self, tr("Save as template"), tr("Template name:"), text=last
        )

        return name.strip() if accepted and name.strip() else None

    def _confirm_replace(self, name: str) -> bool:
        answer = QMessageBox.question(
            self,
            tr("Save as template"),
            tr("A template named “{name}” already exists. Replace it?", name=name),
        )

        return answer == QMessageBox.StandardButton.Yes

    def _confirm_delete(self, name: str) -> bool:
        answer = QMessageBox.question(
            self, tr("Delete template"), tr("Delete the template “{name}”?", name=name)
        )

        return answer == QMessageBox.StandardButton.Yes

    def _length_input(self) -> QDoubleSpinBox:
        spin_box = QDoubleSpinBox(self)
        spin_box.setRange(0.0, 100.0)
        spin_box.setDecimals(1)
        spin_box.setSingleStep(0.1)
        spin_box.setSuffix(" m")

        return spin_box

    def _direction_input(self) -> QComboBox:
        combo_box = QComboBox(self)
        combo_box.addItem(tr("Left to right"), True)
        combo_box.addItem(tr("Right to left"), False)

        return combo_box

    def _direction_inputs(self):
        return (self.entry_direction_input, self.exit_direction_input)

    def area_label(self, index: int, area: IndoorArea) -> str:
        return f"{index + 1} – {area.name}"

    def _fill_areas(self):
        """The areas in the order their markers are numbered, from the open side."""

        order = [area for row in rows(self.areas, self.side_input.currentData()) for area in row]
        self.area_input.blockSignals(True)
        self.area_input.clear()

        for index, area in enumerate(order):
            self.area_input.addItem(self.area_label(index, area), area)

        self.area_input.setCurrentIndex(order.index(self.area))
        self.area_input.blockSignals(False)

    def _area_chosen(self):
        self.area = self.area_input.currentData()
        self._update()

    def _update(self):
        self.area_plan = None
        settings = self.settings
        back_in = settings.mode == ParkingMode.BACK_IN

        self.side_label.setText(tr("Open side:") if back_in else tr("Entry side:"))
        self.back_label.setText(tr("Back wall:") if back_in else tr("Exit offset:"))
        self.gap_input.setEnabled(settings.bays > 1)
        self._show_all_gaps()
        self.form.setRowVisible(self.positions_input, not back_in)
        self.form.setRowVisible(self.spacing_input, not back_in)
        self.spacing_input.setEnabled(settings.positions > 1)

        frame = ShedFrame.from_area(self.area, settings.open_side)
        width = bay_width(frame, settings)
        too_narrow = width < MIN_BAY_WIDTH
        inside = settings.back_offset < frame.depth
        marker_d = marker_depth(frame, settings)
        line = bay_line(frame, settings) if inside else None
        line_fits = not back_in or not inside or line.fits(marker_d)
        positions_inside = not inside or positions_fit(frame, settings)

        self.bay_width_label.setText(f"{self.locale().toString(width, 'f', 1)} m")
        self.bay_width_label.setStyleSheet("color: red;" if too_narrow else "")

        problem = self._problem(settings, frame, too_narrow, line_fits, positions_inside)
        fits = not too_narrow and inside and line_fits and positions_inside
        network = plan_parking(frame, settings) if fits else None

        self.preview.show_plan(self.area, frame, settings, network)
        self.create_button.setEnabled(problem is None)

        if not inside or not positions_inside:
            self.side_view.clear()
        elif back_in:
            self.side_view.show_bay_line(frame, settings, line)
        else:
            self.side_view.show_drive_through(frame, settings, *drive_through_line(frame, settings))

        if problem is None and settings.group not in self.groups:
            self.hint_label.setText(tr("The group “{name}” will be created.", name=settings.group))
        else:
            self.hint_label.setText(problem or "")

        self.area_plan_changed.emit(self.area_plan)

    def _problem(self, settings, frame, too_narrow, line_fits, positions_inside) -> str | None:
        if too_narrow:
            return tr("The bays are narrower than {width} m.", width=f"{MIN_BAY_WIDTH:.1f}")

        if settings.back_offset >= frame.depth:
            return self.MARKER_OUTSIDE_TEXT

        if not positions_inside:
            return tr("The parking positions don't fit in the shed.")

        if not line_fits:
            return self.LINE_INSIDE_TEXT.format(distance=f"{ENTRY_LINE_OUTSIDE:.1f}")

        return self._names_problem(settings)

    def _names_problem(self, settings) -> str | None:
        """Plans all sheds (shown on the map even while the names are missing) and checks the
        names."""

        try:
            self.area_plan = plan_sheds(self.areas, settings)
        except ValueError:
            return tr("The settings don't fit every shed.")

        if not settings.marker_name:
            return self.EMPTY_NAME_TEXT

        if not settings.group:
            return self.EMPTY_GROUP_TEXT

        for _, name, group in self.area_plan.markers:
            if (name, group) in self.taken_names:
                return tr("A marker in this group already has the name “{name}”.", name=name)

        return None

    def _bays_changed(self, bays: int):
        """Keeps the edited gaps; new ones get the "All gaps" value."""

        all_gaps = max(self.gap_input.value(), 0.0)
        self.gaps = (self.gaps + [all_gaps] * bays)[: bays - 1]
        self._update()

    def _all_gaps_changed(self, value: float):
        if value >= 0:
            self.gaps = [value] * (self.bays_input.value() - 1)
            self._update()

    def _show_all_gaps(self):
        if not self.gaps:
            return

        value = self.gaps[0] if len(set(self.gaps)) == 1 else self.gap_input.minimum()
        self.gap_input.blockSignals(True)
        self.gap_input.setValue(value)
        self.gap_input.blockSignals(False)

    def _open_side(self, side: str):
        self.side_input.setCurrentIndex(self.side_input.findData(side))

    def _edit_shed_length(self, key, position: QPoint):
        """Opens a spin box at the click for a wall offset, or for a gap given by its index."""

        inputs = {"left": self.left_input, "right": self.right_input, "back": self.back_input}

        if key in inputs:
            self._open_popup(inputs[key].value(), 0.0, inputs[key].setValue, position)
            return

        def set_gap(value):
            self.gaps[key] = value
            self._update()

        self._open_popup(self.gaps[key], 0.0, set_gap, position)

    def _edit_segment(self, part: str, index: int, position: QPoint):
        """Opens a spin box at the click for a segment ("segment") or turn step ("turn")."""

        settings = self.settings
        line = bay_line(ShedFrame.from_area(self.area, settings.open_side), settings)

        if part == "segment":
            value, change = line.segments[index], line.with_segment
        else:
            value, change = line.turn[index], line.with_turn_step

        self._open_popup(
            value, 0.1, lambda length: self._set_bay_line(change(index, length)), position
        )

    def _set_bay_line(self, line: BayLine):
        self.bay_line = line
        self._update()

    def _open_popup(self, value: float, minimum: float, apply, position: QPoint):
        self.popup = LengthPopup(value, minimum, apply, self)
        self.popup.move(position)
        self.popup.show()
        self.popup.setFocus()
        self.popup.selectAll()


class LengthPopup(QDoubleSpinBox):
    """Spin box at the clicked spot of a preview: Enter applies, Esc or a click elsewhere
    cancels."""

    def __init__(self, value: float, minimum: float, apply, parent=None):
        super().__init__(parent)

        self.setWindowFlags(Qt.Popup)
        self.setRange(minimum, 100.0)
        self.setDecimals(1)
        self.setSingleStep(0.1)
        self.setSuffix(" m")
        self.setValue(value)
        self.apply = apply

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.interpretText()
            self.close()
            self.apply(self.value())
        elif event.key() == Qt.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)
