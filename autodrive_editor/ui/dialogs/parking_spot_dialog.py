import math
from dataclasses import replace

from PySide6.QtCore import QPoint, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from autodrive_editor.editing.parking_layout import (
    ENTRY_BRANCH_BACK,
    ENTRY_LINE_INSIDE,
    ENTRY_LINE_OUTSIDE,
    EXIT_BRANCH_ALONG,
    EXIT_LINE_OUTSIDE,
    MIN_BAY_WIDTH,
    SIDE_CORNERS,
    BayLine,
    ParkingMode,
    ParkingNetwork,
    ParkingSettings,
    ShedFrame,
    bay_centers,
    bay_line,
    bay_width,
    default_open_side,
    drive_through_line,
    marker_depth,
    plan_parking,
    side_angle,
)
from autodrive_editor.file_io.savegame_sheds import IndoorArea
from autodrive_editor.i18n import tr
from autodrive_editor.model.connections import ConnectionType
from autodrive_editor.rendering.display_style import DisplayStyle

SIDE_NAMES = {"front": tr("Front"), "back": tr("Back"), "left": tr("Left"), "right": tr("Right")}

COMPASS_NAMES = (
    tr("north"),
    tr("north-east"),
    tr("east"),
    tr("south-east"),
    tr("south"),
    tr("south-west"),
    tr("west"),
    tr("north-west"),
)

# Bay width the default number of bays is based on (marker G1 of the example route).
DEFAULT_BAY_WIDTH = 6.6
DEFAULTS = ParkingSettings()


def compass_name(angle: float) -> str:
    return COMPASS_NAMES[round(angle / 45) % 8]


class ParkingSpotDialog(QDialog):
    """Asks how the parking spots of a shed are laid out and named, with a live top view."""

    EMPTY_NAME_TEXT = tr("Please enter a marker name.")
    EMPTY_GROUP_TEXT = tr("Please choose or enter a group.")

    def __init__(
        self,
        area: IndoorArea,
        groups: list[str],
        taken_names: set[tuple[str, str]],
        parent=None,
    ):
        super().__init__(parent)

        self.setWindowTitle(tr("Create parking spots"))

        self.area = area
        self.groups = list(groups)
        self.taken_names = set(taken_names)

        self.mode_input = QComboBox(self)
        self.mode_input.addItem(tr("Back in"), ParkingMode.BACK_IN)
        self.mode_input.addItem(tr("Drive through"), ParkingMode.DRIVE_THROUGH)

        self.side_input = QComboBox(self)

        for side, name in SIDE_NAMES.items():
            compass = compass_name(side_angle(area, side))
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
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        self.reset_button.clicked.connect(self.reset_shed_settings)

        form = QFormLayout()
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

        for widget in (self.mode_input, self.side_input) + self._direction_inputs():
            widget.currentIndexChanged.connect(self._update)

        for widget in (self.start_input, self.left_input, self.right_input, self.back_input):
            widget.valueChanged.connect(self._update)

        self.bays_input.valueChanged.connect(self._bays_changed)
        self.gap_input.valueChanged.connect(self._all_gaps_changed)

        self.name_input.textChanged.connect(self._update)
        self.group_input.currentTextChanged.connect(self._update)

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
        self.gap_input.setValue(0.0)
        self.gaps = [0.0] * (self.bays_input.value() - 1)
        self.bay_line = None
        self._update()

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

    def _update(self):
        settings = self.settings
        back_in = settings.mode == ParkingMode.BACK_IN

        self.side_label.setText(tr("Open side:") if back_in else tr("Entry side:"))
        self.back_label.setText(tr("Back wall:") if back_in else tr("Exit offset:"))
        self.gap_input.setEnabled(settings.bays > 1)
        self._show_all_gaps()

        frame = ShedFrame.from_area(self.area, settings.open_side)
        width = bay_width(frame, settings)
        too_narrow = width < MIN_BAY_WIDTH
        inside = settings.back_offset < frame.depth
        marker_d = marker_depth(frame, settings)
        line = bay_line(frame, settings) if inside else None
        line_fits = not back_in or not inside or line.fits(marker_d)

        self.bay_width_label.setText(f"{self.locale().toString(width, 'f', 1)} m")
        self.bay_width_label.setStyleSheet("color: red;" if too_narrow else "")

        problem = self._problem(settings, frame, too_narrow, line_fits)
        fits = not too_narrow and inside and line_fits
        network = plan_parking(frame, settings) if fits else None

        self.preview.show_plan(self.area, frame, settings, network)
        self.create_button.setEnabled(problem is None)

        if not inside:
            self.side_view.clear()
        elif back_in:
            self.side_view.show_bay_line(frame, settings, line)
        else:
            self.side_view.show_drive_through(frame, settings, *drive_through_line(frame, settings))

        if problem is None and settings.group not in self.groups:
            self.hint_label.setText(tr("The group “{name}” will be created.", name=settings.group))
        else:
            self.hint_label.setText(problem or "")

    def _problem(self, settings, frame, too_narrow, line_fits) -> str | None:
        if too_narrow:
            return tr("The bays are narrower than {width} m.", width=f"{MIN_BAY_WIDTH:.1f}")

        if settings.back_offset >= frame.depth:
            return tr("The marker must be inside the shed.")

        if not line_fits:
            return tr(
                "The entry line must be at least {distance} m outside the shed.",
                distance=f"{ENTRY_LINE_OUTSIDE:.1f}",
            )

        if not settings.marker_name:
            return self.EMPTY_NAME_TEXT

        if not settings.group:
            return self.EMPTY_GROUP_TEXT

        for number in range(settings.start_number, settings.start_number + settings.bays):
            name = f"{settings.marker_name} {number}"

            if (name, settings.group) in self.taken_names:
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


class ParkingPreview(QWidget):
    """Top view of the shed with the open side at the bottom, and the network to be created.
    Walls, offset strips and gaps can be clicked to edit them, side labels to open that side."""

    side_clicked = Signal(str)
    # "left", "right", "back" or the index of a gap, and where the click was on the screen.
    length_clicked = Signal(object, QPoint)

    MARGIN_PX = 16
    # Room around the shed for the side labels, and on the right for the north arrow.
    LABEL_WIDTH_PX = 80
    LABEL_HEIGHT_PX = 32
    NORTH_PX = 48
    # Walls and gaps narrower than this on screen are widened for clicking.
    CLICK_PX = 8
    NODE_PX = 4
    MARKER_PX = 8
    ARROW_PX = 7

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setMinimumSize(480, 400)
        self.setMouseTracking(True)

        self.area: IndoorArea | None = None
        self.frame: ShedFrame | None = None
        self.settings: ParkingSettings | None = None
        self.network: ParkingNetwork | None = None

    def show_plan(self, area: IndoorArea, frame: ShedFrame, settings: ParkingSettings, network):
        self.area, self.frame, self.settings, self.network = area, frame, settings, network
        self.update()

    def side_labels(self) -> dict[str, QRectF]:
        """Where the label of each side is drawn."""

        frame, to_screen = self.frame, self._transform()
        top_left = to_screen(0, frame.depth)
        bottom_right = to_screen(frame.length, 0)
        middle = (top_left + bottom_right) / 2
        width, height = self.LABEL_WIDTH_PX, self.LABEL_HEIGHT_PX
        rectangles = {
            "bottom": QRectF(middle.x() - width, self.height() - height, 2 * width, height),
            "top": QRectF(middle.x() - width, top_left.y() - height, 2 * width, height),
            "left": QRectF(top_left.x() - width - 4, middle.y() - height / 2, width, height),
            "right": QRectF(bottom_right.x() + 4, middle.y() - height / 2, width, height),
        }

        return {side: rectangles[self._screen_side(side)] for side in SIDE_CORNERS}

    def length_areas(self) -> list[tuple[object, QRectF]]:
        """Clickable areas of the gaps and of the walls with their offset strips."""

        frame, settings, to_screen = self.frame, self.settings, self._transform()
        width = bay_width(frame, settings)
        areas = []

        def area(key, a1, d1, a2, d2, widen_a=0, widen_d=0):
            rectangle = QRectF(to_screen(a1, d1), to_screen(a2, d2)).normalized()
            extra_x = max(0.0, (self.CLICK_PX - rectangle.width()) / 2) if widen_a else 0.0
            extra_y = max(0.0, (self.CLICK_PX - rectangle.height()) / 2) if widen_d else 0.0
            areas.append((key, rectangle.adjusted(-extra_x, -extra_y, extra_x, extra_y)))

        if width > 0:
            for index, center in enumerate(bay_centers(frame, settings)[:-1]):
                start = center + width / 2
                area(index, start, 0, start + settings.gaps[index], frame.depth, widen_a=1)

        area("left", 0, 0, settings.left_offset, frame.depth, widen_a=1)
        area("right", frame.length - settings.right_offset, 0, frame.length, frame.depth, 1)
        area("back", 0, marker_depth(frame, settings), frame.length, frame.depth, widen_d=1)

        return areas

    def mousePressEvent(self, event):
        if self.frame is None or event.button() != Qt.LeftButton:
            return

        key = self._clickable(event.position())

        if key is None:
            return

        if key in SIDE_CORNERS:
            self.side_clicked.emit(key)
        else:
            self.length_clicked.emit(key[0], event.globalPosition().toPoint())

    def mouseMoveEvent(self, event):
        if self.frame is not None:
            clickable = self._clickable(event.position()) is not None
            self.setCursor(Qt.PointingHandCursor if clickable else Qt.ArrowCursor)

    def _clickable(self, position: QPointF):
        """The side of a clicked label, or (key,) of a clicked length area."""

        for side, rectangle in self.side_labels().items():
            if side != self.settings.open_side and rectangle.contains(position):
                return side

        for key, rectangle in self.length_areas():
            if rectangle.contains(position):
                return (key,)

        return None

    def paintEvent(self, event):
        if self.frame is None:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.fillRect(self.rect(), self.palette().base())

        frame, settings = self.frame, self.settings
        style = DisplayStyle()
        to_screen = self._transform()

        # Shed and bays.
        shed_color = QColor(*style.shed_color)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(*style.shed_color, style.shed_fill_alpha))
        painter.drawPolygon(self._rectangle(to_screen, 0, 0, frame.length, frame.depth))

        width = bay_width(frame, settings)

        if width > 0:
            painter.setBrush(QColor(*style.shed_color, 2 * style.shed_fill_alpha))

            for center in bay_centers(frame, settings):
                bay = self._rectangle(to_screen, center - width / 2, 0, width, frame.depth)
                painter.drawPolygon(bay)

        # Walls: the open side (and the exit side when driving through) is dashed.
        corners = [to_screen(a, d) for a, d in ((0, 0), (frame.length, 0))]
        corners += [to_screen(a, d) for a, d in ((frame.length, frame.depth), (0, frame.depth))]
        exit_open = settings.mode == ParkingMode.DRIVE_THROUGH

        for index in range(4):
            is_open = index == 0 or (index == 2 and exit_open)
            pen = QPen(shed_color, 1.5 if is_open else 3, Qt.DashLine if is_open else Qt.SolidLine)
            painter.setPen(pen)
            painter.drawLine(corners[index], corners[(index + 1) % 4])

        if self.network is not None:
            self._paint_network(painter, to_screen, style)

        self._paint_side_labels(painter)
        self._paint_north(painter)

        painter.end()

    def _paint_network(self, painter, to_screen, style):
        network = self.network
        points = [to_screen(a, d) for a, d in network.points]

        for source, target, connection_type in network.connections:
            paint_connection(painter, points[source], points[target], connection_type, style)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(*style.subprio_node_color))

        for point in points:
            painter.drawEllipse(point, self.NODE_PX / 2, self.NODE_PX / 2)

        painter.setBrush(MARKER_COLOR)

        for index, _ in network.markers:
            painter.drawEllipse(points[index], self.MARKER_PX / 2, self.MARKER_PX / 2)

    def _paint_side_labels(self, painter):
        font = painter.font()

        for side, rectangle in self.side_labels().items():
            is_open = side == self.settings.open_side
            font.setBold(is_open)
            painter.setFont(font)
            painter.setPen(self.palette().text().color())
            compass = compass_name(side_angle(self.area, side))
            text = f"{SIDE_NAMES[side]}\n({compass})"
            painter.drawText(rectangle, Qt.AlignCenter, text)

        font.setBold(False)
        painter.setFont(font)

    def _paint_north(self, painter):
        """Arrow pointing to the top of the map, so the sides can be found on the map."""

        a, d = self.frame.map_direction(0, -1)
        direction = QPointF(a, -d)
        center = QPointF(self.width() - 28, 28)
        tip = center + direction * 14

        painter.setPen(QPen(self.palette().text().color(), 1.5))
        painter.drawLine(center - direction * 14, tip)
        painter.setBrush(self.palette().text().color())
        painter.drawPolygon(arrow_head(center, tip, self.ARROW_PX))
        painter.drawText(QRectF(center.x() - 30, center.y() + 14, 60, 16), Qt.AlignCenter, tr("N"))

    def _screen_side(self, side: str) -> str:
        """Where a side of the building is in the view: "bottom" is the open side."""

        corners = self.area.corners
        start, end = (corners[index] for index in SIDE_CORNERS[side])
        x, z = ((start[i] + end[i]) / 2 - self.frame.origin[i] for i in range(2))
        a, d = self.frame.map_direction(x, z)

        if d < self.frame.depth / 4:
            return "bottom"

        if d > self.frame.depth * 3 / 4:
            return "top"

        return "left" if a < self.frame.length / 2 else "right"

    def _transform(self):
        """Function from (a, d) to screen, fitting the shed and the network into the widget."""

        frame = self.frame
        points = [(0.0, 0.0), (frame.length, frame.depth)]

        if self.network is not None:
            points += self.network.points

        min_a = min(a for a, _ in points)
        max_a = max(a for a, _ in points)
        min_d = min(d for _, d in points)
        max_d = max(d for _, d in points)

        side_x = self.MARGIN_PX + self.LABEL_WIDTH_PX
        side_y = self.MARGIN_PX + self.LABEL_HEIGHT_PX
        scale = min(
            (self.width() - 2 * side_x - self.NORTH_PX) / max(max_a - min_a, 1.0),
            (self.height() - 2 * side_y) / max(max_d - min_d, 1.0),
        )
        offset_x = (self.width() - self.NORTH_PX - (max_a - min_a) * scale) / 2
        offset_y = (self.height() - (max_d - min_d) * scale) / 2

        def to_screen(a: float, d: float) -> QPointF:
            return QPointF(offset_x + (a - min_a) * scale, offset_y + (max_d - d) * scale)

        return to_screen

    @staticmethod
    def _rectangle(to_screen, a, d, length, depth) -> QPolygonF:
        corners = ((a, d), (a + length, d), (a + length, d + depth), (a, d + depth))

        return QPolygonF([to_screen(*corner) for corner in corners])


class BayLinePreview(QWidget):
    """Side view of one bay line, outward to the right. Back in: segments can be clicked to edit
    their length, "+" splits a segment, a clicked node is deleted with Delete, and the entry and
    exit branches are dragged to another node. Drive through: shown only."""

    line_changed = Signal(object)
    # "segment" or "turn", its index, and where the click was on the screen.
    length_clicked = Signal(str, int, QPoint)

    MARGIN_PX = 24
    HEIGHT_PX = 150
    NODE_PX = 6
    MARKER_PX = 10
    ARROW_PX = 7
    PLUS_PX = 12
    # The "+" buttons sit this far above the line.
    PLUS_ABOVE_PX = 18
    HANDLE_PX = 10
    CLICK_PX = 7
    WALL_HALF_PX = 40

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setFixedHeight(self.HEIGHT_PX)
        self.setMinimumWidth(480)
        self.setFocusPolicy(Qt.ClickFocus)
        self.setMouseTracking(True)

        self.frame: ShedFrame | None = None
        self.settings: ParkingSettings | None = None
        self.line: BayLine | None = None
        # Drive through: the depths of the nodes and the index of the marker.
        self.depths: list[float] = []
        self.marker = 0
        self.selected: int | None = None
        # "entry" or "exit" while a branch is dragged.
        self.dragging: str | None = None

    def clear(self):
        self.frame = None
        self.update()

    def show_bay_line(self, frame: ShedFrame, settings: ParkingSettings, line: BayLine):
        self.frame, self.settings, self.line = frame, settings, line
        marker_d = marker_depth(frame, settings)
        self.depths = [marker_d - distance for distance in line.distances]
        self.marker = 0

        if self.selected is not None and self.selected > len(line.segments):
            self.selected = None

        self.update()

    def show_drive_through(self, frame, settings, depths: list[float], marker: int):
        self.frame, self.settings, self.line = frame, settings, None
        self.depths, self.marker = depths, marker
        self.selected = self.dragging = None
        self.update()

    # Layout in screen coordinates.

    def node_points(self) -> list[QPointF]:
        """Dual line nodes (back in) or line nodes (drive through)."""

        to_screen = self._transform()

        return [to_screen(d, 0) for d in self.depths]

    def turn_points(self) -> list[QPointF]:
        to_screen = self._transform()
        d = self.depths[-1]
        points = []

        for step in self.line.turn:
            d -= step
            points.append(to_screen(d, 0))

        return points

    def plus_points(self) -> list[QPointF]:
        nodes = self.node_points()

        return [
            QPointF((start.x() + end.x()) / 2, start.y() - self.PLUS_ABOVE_PX)
            for start, end in zip(nodes, nodes[1:], strict=False)
        ]

    def entry_point(self) -> QPointF:
        sign = 1 if self.settings.entry_left_to_right else -1

        return self._transform()(self._entry_d(), -sign * ENTRY_BRANCH_BACK)

    def exit_point(self) -> QPointF:
        sign = 1 if self.settings.exit_left_to_right else -1

        return self._transform()(self._exit_d(), sign * EXIT_BRANCH_ALONG)

    # Mouse and keys.

    def mousePressEvent(self, event):
        if self.line is None or event.button() != Qt.LeftButton:
            return

        position = event.position()
        hit = self._hit(position)

        if hit is None:
            self.selected = None
        elif hit[0] in ("entry", "exit"):
            self.dragging = hit[0]
        elif hit[0] == "plus":
            self.line_changed.emit(self.line.split(hit[1]))
        elif hit[0] == "node":
            self.selected = hit[1]
        else:
            self.length_clicked.emit(hit[0], hit[1], event.globalPosition().toPoint())

        self.update()

    def mouseMoveEvent(self, event):
        if self.line is None:
            return

        if self.dragging is None:
            hit = self._hit(event.position())
            self.setCursor(Qt.ArrowCursor if hit is None else Qt.PointingHandCursor)
            return

        x = event.position().x()
        to_screen = self._transform()

        # The square is on the entry or exit line, which runs a set distance from its node.
        if self.dragging == "entry":
            candidates = self.line.entry_nodes(marker_depth(self.frame, self.settings))
            shift = ENTRY_LINE_INSIDE
        else:
            candidates = self.line.exit_nodes()
            shift = -EXIT_LINE_OUTSIDE

        if not candidates:
            return

        def square_x(node):
            return to_screen(self.depths[node] + shift, 0).x()

        node = min(candidates, key=lambda index: abs(square_x(index) - x))
        field = "entry_node" if self.dragging == "entry" else "exit_node"

        if node != getattr(self.line, field):
            self.line_changed.emit(replace(self.line, **{field: node}))

    def mouseReleaseEvent(self, event):
        self.dragging = None

    def keyPressEvent(self, event):
        line, node = self.line, self.selected

        if event.key() == Qt.Key_Delete and line is not None and node is not None:
            if line.can_remove(node):
                self.selected = None
                self.line_changed.emit(line.remove(node))
        else:
            super().keyPressEvent(event)

    def _hit(self, position: QPointF):
        """What is under the mouse: ("entry"|"exit"|"plus"|"node"|"segment"|"turn", index)."""

        def distance(point):
            return math.dist((point.x(), point.y()), (position.x(), position.y()))

        def near(point, limit):
            return distance(point) <= limit

        if near(self.entry_point(), self.HANDLE_PX):
            return ("entry", 0)

        if near(self.exit_point(), self.HANDLE_PX):
            return ("exit", 0)

        for index, point in enumerate(self.plus_points()):
            if near(point, self.PLUS_PX / 2 + 2):
                return ("plus", index)

        nodes = self.node_points()

        nearest = min(range(len(nodes)), key=lambda index: distance(nodes[index]))

        if distance(nodes[nearest]) <= self.CLICK_PX:
            return ("node", nearest)

        turn = [nodes[-1], *self.turn_points()]

        for part, points in (("segment", nodes), ("turn", turn)):
            for index, (start, end) in enumerate(zip(points, points[1:], strict=False)):
                left, right = sorted((start.x(), end.x()))

                if left <= position.x() <= right and abs(position.y() - start.y()) <= 5:
                    return (part, index)

        return None

    # Painting.

    def paintEvent(self, event):
        if self.frame is None:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.fillRect(self.rect(), self.palette().base())

        style = DisplayStyle()
        to_screen = self._transform()
        self._paint_walls(painter, to_screen, style)

        nodes = self.node_points()
        back_in = self.line is not None
        line_type = ConnectionType.DUAL if back_in else ConnectionType.REGULAR

        for start, end in zip(nodes, nodes[1:], strict=False):
            paint_connection(painter, start, end, line_type, style, self.ARROW_PX)

        others = []

        if back_in:
            others = self._paint_back_in(painter, nodes, style)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(*style.subprio_node_color))

        for point in nodes + others:
            painter.drawEllipse(point, self.NODE_PX / 2, self.NODE_PX / 2)

        painter.setBrush(MARKER_COLOR)
        painter.drawEllipse(nodes[self.marker], self.MARKER_PX / 2, self.MARKER_PX / 2)

        if self.selected is not None:
            painter.setPen(QPen(self.palette().highlight().color(), 2))
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(nodes[self.selected], self.NODE_PX + 1, self.NODE_PX + 1)

        painter.end()

    def _paint_walls(self, painter, to_screen, style):
        """Back wall and open side, or entry and exit side; and the entry and exit lines."""

        frame, back_in = self.frame, self.line is not None
        middle = to_screen(0, 0).y()
        shed_color = QColor(*style.shed_color)
        line_pen = QPen(self.palette().mid().color(), 1)

        for d, is_open in ((0, True), (frame.depth, not back_in)):
            pen = QPen(shed_color, 1.5 if is_open else 3, Qt.DashLine if is_open else Qt.SolidLine)
            painter.setPen(pen)
            x = to_screen(d, 0).x()
            painter.drawLine(
                QPointF(x, middle - self.WALL_HALF_PX), QPointF(x, middle + self.WALL_HALF_PX)
            )

        if not back_in:
            return

        painter.setPen(line_pen)

        for d, text in ((self._entry_d(), tr("Entry line")), (self._exit_d(), tr("Exit line"))):
            x = to_screen(d, 0).x()
            painter.drawLine(QPointF(x, 4), QPointF(x, self.height() - 20))
            painter.drawText(QRectF(x - 50, self.height() - 18, 100, 16), Qt.AlignCenter, text)

    def _paint_back_in(self, painter, nodes, style) -> list[QPointF]:
        """Turn, branches and "+" buttons. Returns the extra nodes."""

        line = self.line
        turn = [nodes[-1], *self.turn_points()]
        reverse_offset = QPointF(0, 5)

        for start, end in zip(turn, turn[1:], strict=False):
            paint_connection(painter, start, end, ConnectionType.REGULAR, style, self.ARROW_PX)

        paint_connection(
            painter,
            turn[-1] + reverse_offset,
            turn[0] + reverse_offset,
            ConnectionType.REVERSE,
            style,
            self.ARROW_PX,
        )

        entry, exit_ = self.entry_point(), self.exit_point()
        regular = ConnectionType.REGULAR
        paint_connection(painter, entry, nodes[line.entry_node], regular, style, self.ARROW_PX)
        paint_connection(painter, nodes[line.exit_node], exit_, regular, style, self.ARROW_PX)

        # Handles to drag the branches.
        painter.setPen(QPen(self.palette().text().color(), 1))
        painter.setBrush(self.palette().button())
        size = self.HANDLE_PX

        for point in (entry, exit_):
            painter.drawRect(QRectF(point.x() - size / 2, point.y() - size / 2, size, size))

        for point in self.plus_points():
            radius = self.PLUS_PX / 2
            painter.drawEllipse(point, radius, radius)
            painter.drawLine(point - QPointF(radius - 3, 0), point + QPointF(radius - 3, 0))
            painter.drawLine(point - QPointF(0, radius - 3), point + QPointF(0, radius - 3))

        return turn[1:]

    def _entry_d(self) -> float:
        return self.line.entry_line_depth(marker_depth(self.frame, self.settings))

    def _exit_d(self) -> float:
        return self.depths[self.line.exit_node] - EXIT_LINE_OUTSIDE

    def _transform(self):
        """Function from (d, a) to screen: outward to the right, a upward."""

        frame = self.frame
        ds = [frame.depth, 0.0, *self.depths]

        if self.line is not None:
            ds += [self.depths[-1] - sum(self.line.turn), self._entry_d(), self._exit_d()]

        min_d, max_d = min(ds), max(ds)
        margin = self.MARGIN_PX
        scale = (self.width() - 2 * margin) / max(max_d - min_d, 1.0)
        # Exaggerated across the line, so the branches can be told apart.
        a_scale = min(max(scale, 10.0), (self.height() / 2 - 30) / 2)
        middle = self.height() / 2

        def to_screen(d: float, a: float) -> QPointF:
            return QPointF(margin + (max_d - d) * scale, middle - a * a_scale)

        return to_screen


MARKER_COLOR = QColor(30, 80, 160)


def paint_connection(painter, start, end, connection_type, style, arrow_px=7):
    colors = {
        ConnectionType.REGULAR: style.regular_connection_color,
        ConnectionType.DUAL: style.dual_connection_color,
        ConnectionType.REVERSE: style.reverse_connection_color,
    }
    color = QColor(*colors[connection_type])
    painter.setPen(QPen(color, 1.5))
    painter.drawLine(start, end)

    if connection_type != ConnectionType.DUAL:
        painter.setBrush(color)
        painter.drawPolygon(arrow_head(start, end, arrow_px))


def arrow_head(start: QPointF, end: QPointF, size: float) -> QPolygonF:
    """Arrow head in the middle of a line, pointing to its end."""

    dx, dy = end.x() - start.x(), end.y() - start.y()
    length = math.hypot(dx, dy)

    if length == 0:
        return QPolygonF()

    ux, uy = dx / length, dy / length
    middle = QPointF((start.x() + end.x()) / 2, (start.y() + end.y()) / 2)
    tip = middle + QPointF(ux, uy) * size / 2
    back = middle - QPointF(ux, uy) * size / 2
    side = QPointF(-uy, ux) * size / 2

    return QPolygonF([tip, back + side, back - side])
