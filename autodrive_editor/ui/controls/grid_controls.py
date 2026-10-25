from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QFormLayout,
    QMenu,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QWidgetAction,
)


class GridControls(QToolButton):
    visibility_requested = Signal(bool)

    spacing_requested = Signal(float)

    rotation_requested = Signal(float)

    reset_requested = Signal()

    def __init__(
        self,
        grid_visible: bool = True,
        grid_spacing: float = 10.0,
        grid_rotation: float = 0.0,
        parent=None,
    ):
        super().__init__(parent)

        self.setText("Raster")

        self.setToolTip("Hintergrundraster einstellen")

        self.setPopupMode(QToolButton.InstantPopup)

        self._create_menu()

        self.set_grid_visible(grid_visible)

        self.set_grid_spacing(grid_spacing)

        self.set_grid_rotation(grid_rotation)

    def _create_menu(self):
        self.grid_menu = QMenu(self)

        self.visibility_input = QCheckBox("Raster anzeigen")

        self.visibility_input.toggled.connect(self._emit_visibility)

        self.spacing_input = QDoubleSpinBox()

        self.spacing_input.setRange(0.1, 10000.0)

        self.spacing_input.setDecimals(2)

        self.spacing_input.setSingleStep(1.0)

        self.spacing_input.setSuffix(" m")

        self.spacing_input.setKeyboardTracking(False)

        self.spacing_input.editingFinished.connect(self._emit_spacing)

        self.rotation_input = QDoubleSpinBox()

        self.rotation_input.setRange(0.0, 360.0)

        self.rotation_input.setDecimals(2)

        self.rotation_input.setSingleStep(1.0)

        self.rotation_input.setSuffix("°")

        self.rotation_input.setWrapping(True)

        self.rotation_input.setKeyboardTracking(False)

        self.rotation_input.editingFinished.connect(self._emit_rotation)

        form_layout = QFormLayout()

        form_layout.addRow("Rasterabstand:", self.spacing_input)

        form_layout.addRow("Rasterrotation:", self.rotation_input)

        reset_button = QPushButton("Raster zurücksetzen")

        reset_button.clicked.connect(self._request_reset)

        content_layout = QVBoxLayout()

        content_layout.addWidget(self.visibility_input)

        content_layout.addLayout(form_layout)

        content_layout.addWidget(reset_button)

        content_widget = QWidget()

        content_widget.setMinimumWidth(280)

        content_widget.setLayout(content_layout)

        controls_action = QWidgetAction(self.grid_menu)

        controls_action.setDefaultWidget(content_widget)

        self.grid_menu.addAction(controls_action)

        self.setMenu(self.grid_menu)

    def set_grid_visible(self, visible: bool):
        visible = bool(visible)

        self.visibility_input.blockSignals(True)

        self.visibility_input.setChecked(visible)

        self.visibility_input.blockSignals(False)

        self._update_button_text()

    def set_grid_spacing(self, spacing: float):
        self.spacing_input.blockSignals(True)

        self.spacing_input.setValue(float(spacing))

        self.spacing_input.blockSignals(False)

    def set_grid_rotation(self, rotation_angle: float):
        normalized_angle = float(rotation_angle) % 360.0

        self.rotation_input.blockSignals(True)

        self.rotation_input.setValue(normalized_angle)

        self.rotation_input.blockSignals(False)

    def _emit_visibility(self, visible: bool):
        self._update_button_text()

        self.visibility_requested.emit(visible)

    def _emit_spacing(self):
        self.spacing_input.interpretText()

        self.spacing_requested.emit(self.spacing_input.value())

    def _emit_rotation(self):
        self.rotation_input.interpretText()

        rotation_angle = self.rotation_input.value()

        if rotation_angle >= 360.0:
            rotation_angle = 0.0

        self.set_grid_rotation(rotation_angle)

        self.rotation_requested.emit(rotation_angle)

    def _request_reset(self):
        self.reset_requested.emit()

        self.grid_menu.close()

    def _update_button_text(self):
        if self.visibility_input.isChecked():
            self.setText("Raster an")

        else:
            self.setText("Raster aus")
