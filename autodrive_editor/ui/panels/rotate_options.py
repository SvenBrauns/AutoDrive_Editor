from PySide6.QtCore import Signal
from PySide6.QtWidgets import QDoubleSpinBox, QFormLayout, QWidget

from autodrive_editor.i18n import tr


class RotateOptionsWidget(QWidget):
    """The snap step of the Rotate tool, shown from the arrow of its button."""

    snap_angle_changed = Signal(float)

    def __init__(self, snap_angle: float, parent=None):
        super().__init__(parent)

        self.snap_angle_box = QDoubleSpinBox(self)
        self.snap_angle_box.setRange(0.1, 180.0)
        self.snap_angle_box.setDecimals(1)
        self.snap_angle_box.setSuffix("°")
        self.snap_angle_box.setToolTip(tr("Step while Shift is held during rotating"))
        self.snap_angle_box.setValue(snap_angle)
        self.snap_angle_box.valueChanged.connect(self.snap_angle_changed.emit)

        layout = QFormLayout(self)
        layout.addRow(tr("Snap step (Shift):"), self.snap_angle_box)
