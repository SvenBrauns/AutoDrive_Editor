from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QDoubleSpinBox, QHBoxLayout, QLabel, QPushButton, QWidget

from autodrive_editor.editing.parallel_lane import ParallelLaneOptions
from autodrive_editor.i18n import tr
from autodrive_editor.model.autodrive_data import REGULAR_FLAG, SUBPRIO_FLAG


def _metres_box(parent, minimum: float, maximum: float, tooltip: str) -> QDoubleSpinBox:
    box = QDoubleSpinBox(parent)
    box.setRange(minimum, maximum)
    box.setSingleStep(0.5)
    box.setDecimals(1)
    box.setSuffix(" m")
    box.setToolTip(tooltip)
    return box


class ParallelLaneOptionsWidget(QWidget):
    """Distance, direction, node spacing and node type of the parallel lane, and a button that
    creates it. The pointer also sets the distance; set_distance() shows it here."""

    options_changed = Signal(object)
    apply_requested = Signal()

    def __init__(self, options: ParallelLaneOptions, parent=None):
        super().__init__(parent)

        self.distance_box = _metres_box(self, 0.5, 100.0, tr("Distance of the new lane"))
        self.direction_box = QComboBox(self)
        self.direction_box.setToolTip(tr("Driving direction of the new lane"))
        self.direction_box.addItem(tr("Same"), False)
        self.direction_box.addItem(tr("Opposite"), True)
        self.spacing_box = _metres_box(self, 0.5, 100.0, tr("Spacing of the new nodes"))
        self.flag_box = QComboBox(self)
        self.flag_box.setToolTip(tr("Type of the new nodes"))
        self.flag_box.addItem("Regular", REGULAR_FLAG)
        self.flag_box.addItem("Subprio", SUBPRIO_FLAG)

        apply_button = QPushButton(tr("Apply"), self)
        apply_button.setToolTip(tr("Create the lane (Enter)"))
        apply_button.clicked.connect(self.apply_requested.emit)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        for title, widget in (
            (tr("Lane distance"), self.distance_box),
            (tr("Direction"), self.direction_box),
            (tr("Spacing"), self.spacing_box),
            (tr("Node type"), self.flag_box),
        ):
            layout.addWidget(QLabel(title, self))
            layout.addWidget(widget)
            layout.addSpacing(8)

        layout.addWidget(apply_button)
        layout.addStretch(1)

        self.distance_box.setValue(options.distance)
        self.direction_box.setCurrentIndex(self.direction_box.findData(options.opposite))
        self.spacing_box.setValue(options.spacing)
        self.flag_box.setCurrentIndex(self.flag_box.findData(options.flag))

        for box in (self.distance_box, self.spacing_box):
            box.valueChanged.connect(self._emit_options)

        for box in (self.direction_box, self.flag_box):
            box.currentIndexChanged.connect(self._emit_options)

    @property
    def options(self) -> ParallelLaneOptions:
        return ParallelLaneOptions(
            distance=self.distance_box.value(),
            opposite=self.direction_box.currentData(),
            spacing=self.spacing_box.value(),
            flag=self.flag_box.currentData(),
        )

    def set_distance(self, distance: float):
        """Shows the distance the pointer set, without sending it back."""

        self.distance_box.blockSignals(True)
        self.distance_box.setValue(distance)
        self.distance_box.blockSignals(False)

    def _emit_options(self):
        self.options_changed.emit(self.options)
