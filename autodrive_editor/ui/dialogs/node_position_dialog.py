from PySide6.QtWidgets import QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout, QVBoxLayout


class NodePositionDialog(QDialog):
    """Asks for a node's exact X, Y (height) and Z."""

    LIMIT = 100_000.0
    DECIMALS = 3

    def __init__(self, node_id: int, x: float, y: float, z: float, parent=None):
        super().__init__(parent)

        self.setWindowTitle(f"Position von Node {node_id}")

        self.x_input = self._spin_box(x)
        self.y_input = self._spin_box(y)
        self.z_input = self._spin_box(z)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        form = QFormLayout()
        form.addRow("X:", self.x_input)
        form.addRow("Y (Höhe):", self.y_input)
        form.addRow("Z:", self.z_input)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

        self.x_input.setFocus()
        self.x_input.selectAll()

    @property
    def values(self) -> tuple[float, float, float]:
        return self.x_input.value(), self.y_input.value(), self.z_input.value()

    def _spin_box(self, value: float) -> QDoubleSpinBox:
        spin_box = QDoubleSpinBox(self)
        spin_box.setRange(-self.LIMIT, self.LIMIT)
        spin_box.setDecimals(self.DECIMALS)
        spin_box.setValue(value)
        spin_box.setMinimumWidth(140)
        return spin_box
