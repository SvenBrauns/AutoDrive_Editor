from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QDoubleSpinBox, QHBoxLayout, QLabel, QPushButton, QWidget

from autodrive_editor.editing.path_shapes import PathOptions
from autodrive_editor.i18n import tr
from autodrive_editor.model.autodrive_data import REGULAR_FLAG, SUBPRIO_FLAG
from autodrive_editor.model.connections import ConnectionType


class PathOptionsWidget(QWidget):
    """Node spacing, connection type and node type of the line and curve
    tools, and a button that creates the pending curve. For the Bézier tool
    it also offers the number of control points."""

    options_changed = Signal(object)

    apply_requested = Signal()

    def __init__(self, options: PathOptions, parent=None):
        super().__init__(parent)

        self._control_points = options.control_points

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.spacing_box = QDoubleSpinBox(self)
        self.spacing_box.setRange(0.5, 100.0)
        self.spacing_box.setSingleStep(0.5)
        self.spacing_box.setDecimals(1)
        self.spacing_box.setSuffix(" m")
        self.spacing_box.setToolTip(tr("Spacing of the new nodes"))

        self.connection_box = QComboBox(self)
        self.connection_box.setToolTip(tr("Connection type of the new path"))

        for connection_type in ConnectionType:
            self.connection_box.addItem(connection_type.name.capitalize(), connection_type.value)

        self.flag_box = QComboBox(self)
        self.flag_box.setToolTip(tr("Type of the new nodes"))
        self.flag_box.addItem("Regular", REGULAR_FLAG)
        self.flag_box.addItem("Subprio", SUBPRIO_FLAG)

        self.control_points_box = QComboBox(self)
        self.control_points_box.setToolTip(tr("1: quadratic curve, 2: cubic curve"))
        self.control_points_box.addItem("1", 1)
        self.control_points_box.addItem("2", 2)

        self.apply_button = QPushButton(tr("Apply"), self)
        self.apply_button.setToolTip(tr("Create curve (Enter)"))
        self.apply_button.clicked.connect(self.apply_requested.emit)

        self.control_points_label = QLabel(tr("Control points"), self)

        for title, widget in (
            (tr("Spacing"), self.spacing_box),
            ("Connection", self.connection_box),
            (tr("Node type"), self.flag_box),
        ):
            layout.addWidget(QLabel(title, self))
            layout.addWidget(widget)
            layout.addSpacing(8)

        layout.addWidget(self.control_points_label)
        layout.addWidget(self.control_points_box)
        layout.addWidget(self.apply_button)
        layout.addStretch(1)
        self.set_control_points_visible(False)

        self.set_options(options)

        self.spacing_box.valueChanged.connect(self._emit_options)
        self.connection_box.currentIndexChanged.connect(self._emit_options)
        self.flag_box.currentIndexChanged.connect(self._emit_options)
        self.control_points_box.currentIndexChanged.connect(self._emit_control_points)

    @property
    def options(self) -> PathOptions:
        return PathOptions(
            spacing=self.spacing_box.value(),
            connection_type=ConnectionType(self.connection_box.currentData()),
            flag=self.flag_box.currentData(),
            control_points=self._control_points,
        )

    def set_options(self, options: PathOptions):
        self.spacing_box.setValue(options.spacing)
        self.connection_box.setCurrentIndex(
            self.connection_box.findData(options.connection_type.value)
        )
        self.flag_box.setCurrentIndex(self.flag_box.findData(options.flag))
        self._control_points = options.control_points
        self.control_points_box.setCurrentIndex(
            self.control_points_box.findData(options.control_points)
        )

    def set_control_points_visible(self, visible: bool):
        self.control_points_label.setVisible(visible)
        self.control_points_box.setVisible(visible)

    def _emit_control_points(self):
        self._control_points = self.control_points_box.currentData()
        self._emit_options()

    def _emit_options(self):
        self.options_changed.emit(self.options)
