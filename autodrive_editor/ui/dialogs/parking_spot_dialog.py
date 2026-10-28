import math

from PySide6.QtCore import QPointF, QRectF, Qt
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
    MIN_BAY_WIDTH,
    ParkingMode,
    ParkingNetwork,
    ParkingSettings,
    ShedFrame,
    bay_centers,
    bay_width,
    default_open_side,
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

        self.preview = ParkingPreview(self)

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

        columns = QHBoxLayout()
        columns.addLayout(form)
        columns.addWidget(self.preview, 1)

        layout = QVBoxLayout(self)
        layout.addLayout(columns)
        layout.addWidget(self.hint_label)
        layout.addWidget(self.buttons)

        self.reset_shed_settings()

        for widget in (self.mode_input, self.side_input) + self._direction_inputs():
            widget.currentIndexChanged.connect(self._update)

        for widget in (self.bays_input, self.start_input) + self._length_inputs():
            widget.valueChanged.connect(self._update)

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
            gaps=(self.gap_input.value(),) * (bays - 1),
            entry_left_to_right=self.entry_direction_input.currentData(),
            exit_left_to_right=self.exit_direction_input.currentData(),
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

    def _length_inputs(self):
        return (self.left_input, self.right_input, self.back_input, self.gap_input)

    def _direction_inputs(self):
        return (self.entry_direction_input, self.exit_direction_input)

    def _update(self):
        settings = self.settings
        back_in = settings.mode == ParkingMode.BACK_IN

        self.side_label.setText(tr("Open side:") if back_in else tr("Entry side:"))
        self.back_label.setText(tr("Back wall:") if back_in else tr("Exit offset:"))
        self.gap_input.setEnabled(settings.bays > 1)

        frame = ShedFrame.from_area(self.area, settings.open_side)
        width = bay_width(frame, settings)
        too_narrow = width < MIN_BAY_WIDTH

        self.bay_width_label.setText(f"{self.locale().toString(width, 'f', 1)} m")
        self.bay_width_label.setStyleSheet("color: red;" if too_narrow else "")

        problem = self._problem(settings, frame, too_narrow)
        fits = not too_narrow and settings.back_offset < frame.depth

        self.preview.show_plan(frame, settings, plan_parking(frame, settings) if fits else None)
        self.create_button.setEnabled(problem is None)

        if problem is None and settings.group not in self.groups:
            self.hint_label.setText(tr("The group “{name}” will be created.", name=settings.group))
        else:
            self.hint_label.setText(problem or "")

    def _problem(self, settings: ParkingSettings, frame: ShedFrame, too_narrow: bool) -> str | None:
        if too_narrow:
            return tr("The bays are narrower than {width} m.", width=f"{MIN_BAY_WIDTH:.1f}")

        if settings.back_offset >= frame.depth:
            return tr("The marker must be inside the shed.")

        if not settings.marker_name:
            return self.EMPTY_NAME_TEXT

        if not settings.group:
            return self.EMPTY_GROUP_TEXT

        for number in range(settings.start_number, settings.start_number + settings.bays):
            name = f"{settings.marker_name} {number}"

            if (name, settings.group) in self.taken_names:
                return tr("A marker in this group already has the name “{name}”.", name=name)

        return None


class ParkingPreview(QWidget):
    """Top view of the shed with the open side at the bottom, and the network to be created."""

    MARGIN_PX = 16
    # Room on the right for the north arrow.
    NORTH_PX = 48
    NODE_PX = 4
    MARKER_PX = 8
    ARROW_PX = 7

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setMinimumSize(360, 360)

        self.frame: ShedFrame | None = None
        self.settings: ParkingSettings | None = None
        self.network: ParkingNetwork | None = None

    def show_plan(self, frame: ShedFrame, settings: ParkingSettings, network):
        self.frame, self.settings, self.network = frame, settings, network
        self.update()

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

        self._paint_north(painter)

        painter.end()

    def _paint_network(self, painter, to_screen, style):
        network = self.network
        points = [to_screen(a, d) for a, d in network.points]
        colors = {
            ConnectionType.REGULAR: style.regular_connection_color,
            ConnectionType.DUAL: style.dual_connection_color,
            ConnectionType.REVERSE: style.reverse_connection_color,
        }

        for source, target, connection_type in network.connections:
            color = QColor(*colors[connection_type])
            painter.setPen(QPen(color, 1.5))
            painter.drawLine(points[source], points[target])

            if connection_type != ConnectionType.DUAL:
                painter.setBrush(color)
                painter.drawPolygon(self._arrow(points[source], points[target]))

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(*style.subprio_node_color))

        for point in points:
            painter.drawEllipse(point, self.NODE_PX / 2, self.NODE_PX / 2)

        painter.setBrush(QColor(30, 80, 160))

        for index, _ in network.markers:
            painter.drawEllipse(points[index], self.MARKER_PX / 2, self.MARKER_PX / 2)

    def _paint_north(self, painter):
        """Arrow pointing to the top of the map, so the sides can be found on the map."""

        a, d = self.frame.map_direction(0, -1)
        direction = QPointF(a, -d)
        center = QPointF(self.width() - 28, 28)
        tip = center + direction * 14

        painter.setPen(QPen(self.palette().text().color(), 1.5))
        painter.drawLine(center - direction * 14, tip)
        painter.setBrush(self.palette().text().color())
        painter.drawPolygon(self._arrow(center, tip))
        painter.drawText(QRectF(center.x() - 30, center.y() + 14, 60, 16), Qt.AlignCenter, tr("N"))

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

        margin = self.MARGIN_PX
        scale = min(
            (self.width() - 2 * margin - self.NORTH_PX) / max(max_a - min_a, 1.0),
            (self.height() - 2 * margin) / max(max_d - min_d, 1.0),
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

    def _arrow(self, start: QPointF, end: QPointF) -> QPolygonF:
        """Arrow head in the middle of a line, pointing to its end."""

        dx, dy = end.x() - start.x(), end.y() - start.y()
        length = math.hypot(dx, dy)

        if length == 0:
            return QPolygonF()

        ux, uy = dx / length, dy / length
        middle = QPointF((start.x() + end.x()) / 2, (start.y() + end.y()) / 2)
        size = self.ARROW_PX
        tip = middle + QPointF(ux, uy) * size / 2
        back = middle - QPointF(ux, uy) * size / 2
        side = QPointF(-uy, ux) * size / 2

        return QPolygonF([tip, back + side, back - side])
