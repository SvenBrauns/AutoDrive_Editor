from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QFormLayout,
    QMenu,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QWidgetAction,
)

from autodrive_editor.i18n import tr


class RotationControls(QToolButton):
    """Toolbar menu for the view rotation angle and rotation step."""

    rotation_angle_requested = Signal(float)

    rotation_step_requested = Signal(float)

    reset_requested = Signal()

    def __init__(self, rotation_angle: float = 0.0, rotation_step: float = 1.0, parent=None):
        super().__init__(parent)

        self.setText(tr("Rotation"))

        self.setToolTip(tr("Set the rotation and the rotation step"))

        self.setPopupMode(QToolButton.InstantPopup)

        self._create_menu()
        self.set_rotation_step(rotation_step)
        self.set_rotation_angle(rotation_angle)

    def _create_menu(self):
        self.rotation_menu = QMenu(self)

        self.rotation_angle_input = self._create_angle_input(
            minimum=0.0, maximum=360.0, value=0.0, step=1.0
        )

        self.rotation_angle_input.setWrapping(True)

        self.rotation_angle_input.editingFinished.connect(self._emit_rotation_angle)

        self.rotation_step_input = self._create_angle_input(
            minimum=0.0, maximum=90.0, value=1.0, step=0.1
        )

        self.rotation_step_input.setToolTip(tr("0° means free rotation"))

        self.rotation_step_input.editingFinished.connect(self._emit_rotation_step)

        form_layout = QFormLayout()

        form_layout.addRow(tr("Angle:"), self.rotation_angle_input)

        form_layout.addRow(tr("Rotation step:"), self.rotation_step_input)

        reset_button = QPushButton(tr("Reset rotation"))

        reset_button.clicked.connect(self._request_reset)

        content_layout = QVBoxLayout()

        content_layout.addLayout(form_layout)

        content_layout.addWidget(reset_button)

        content_widget = QWidget()

        content_widget.setMinimumWidth(280)

        content_widget.setLayout(content_layout)

        controls_action = QWidgetAction(self.rotation_menu)

        controls_action.setDefaultWidget(content_widget)

        self.rotation_menu.addAction(controls_action)

        self.setMenu(self.rotation_menu)

    def set_rotation_angle(self, rotation_angle: float):
        normalized_angle = float(rotation_angle) % 360.0

        self.rotation_angle_input.blockSignals(True)

        self.rotation_angle_input.setValue(normalized_angle)

        self.rotation_angle_input.blockSignals(False)

        self.setText(tr("Rotation {angle:.2f}°", angle=normalized_angle))

    def set_rotation_step(self, rotation_step: float):
        rotation_step = max(0.0, float(rotation_step))

        self.rotation_step_input.blockSignals(True)

        self.rotation_step_input.setValue(rotation_step)

        self.rotation_step_input.blockSignals(False)

        angle_input_step = rotation_step if rotation_step > 0.0 else 0.1

        self.rotation_angle_input.setSingleStep(angle_input_step)

    def _emit_rotation_angle(self):
        self.rotation_angle_input.interpretText()

        rotation_angle = self.rotation_angle_input.value()

        if rotation_angle >= 360.0:
            rotation_angle = 0.0

        self.set_rotation_angle(rotation_angle)

        self.rotation_angle_requested.emit(rotation_angle)

    def _emit_rotation_step(self):
        self.rotation_step_input.interpretText()

        self.rotation_step_requested.emit(self.rotation_step_input.value())

    def _request_reset(self):
        self.reset_requested.emit()

        self.rotation_menu.close()

    @staticmethod
    def _create_angle_input(
        minimum: float, maximum: float, value: float, step: float
    ) -> QDoubleSpinBox:
        spin_box = QDoubleSpinBox()

        spin_box.setRange(minimum, maximum)

        spin_box.setDecimals(2)

        spin_box.setSingleStep(step)

        spin_box.setValue(value)

        spin_box.setSuffix("°")

        spin_box.setKeyboardTracking(False)

        return spin_box
