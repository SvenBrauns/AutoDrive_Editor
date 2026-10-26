from dataclasses import replace

from PySide6.QtCore import Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QColorDialog,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from autodrive_editor.i18n import tr
from autodrive_editor.rendering.display_style import DisplayStyle


class ColorButton(QPushButton):
    """A button that shows a color and opens a color picker."""

    color_changed = Signal(tuple)

    def __init__(self, color: tuple[int, int, int], parent=None):
        super().__init__(parent)

        self._color = color

        self.clicked.connect(self._select_color)

        self._update_appearance()

    @property
    def color(self) -> tuple[int, int, int]:
        return self._color

    def set_color(self, color: tuple[int, int, int]):
        self._color = (int(color[0]), int(color[1]), int(color[2]))

        self._update_appearance()

    def _select_color(self):
        initial_color = QColor(self._color[0], self._color[1], self._color[2])

        selected_color = QColorDialog.getColor(initial_color, self, tr("Choose color"))

        if not selected_color.isValid():
            return

        self.set_color((selected_color.red(), selected_color.green(), selected_color.blue()))

        self.color_changed.emit(self._color)

    def _update_appearance(self):
        red, green, blue = self._color

        brightness = red * 0.299 + green * 0.587 + blue * 0.114

        text_color = "black" if brightness >= 150 else "white"

        self.setText(f"RGB {red}, {green}, {blue}")

        self.setStyleSheet(
            f"""
            QPushButton {{
                background-color: rgb(
                    {red},
                    {green},
                    {blue}
                );
                color: {text_color};
                padding: 5px;
                border: 1px solid #666666;
            }}
            """
        )


# Sizes in metres grow with the zoom; sizes in pixels are limits on screen. Each group:
# (title, (field, label, minimum, maximum, step) per size, (field, label) per color).
OPTION_GROUPS = (
    (
        tr("Nodes"),
        (
            ("node_diameter", tr("Diameter (m):"), 0.1, 100.0, 0.1),
            ("node_max_px", tr("Largest on screen (px):"), 1.0, 200.0, 1.0),
            ("node_border_width", tr("Border width (m):"), 0.0, 20.0, 0.05),
            ("node_fade_end_px", tr("Fully shown from (px):"), 0.0, 50.0, 0.5),
            ("selected_node_min_px", tr("Selected, smallest on screen (px):"), 1.0, 50.0, 1.0),
            ("selected_node_ring_width", tr("Selection ring width (m):"), 0.0, 20.0, 0.05),
        ),
        (),
    ),
    (
        tr("Connections"),
        (
            ("connection_width", tr("Width (m):"), 0.01, 20.0, 0.05),
            ("connection_min_px", tr("Thinnest on screen (px):"), 0.5, 20.0, 0.5),
            ("connection_max_px", tr("Thickest on screen (px):"), 0.5, 50.0, 0.5),
            ("arrow_length", tr("Arrow length (m):"), 0.1, 100.0, 0.1),
            ("arrow_min_px", tr("Smallest arrow (px):"), 1.0, 100.0, 1.0),
            ("arrow_max_px", tr("Largest arrow (px):"), 1.0, 100.0, 1.0),
        ),
        (
            ("regular_connection_color", tr("Regular color:")),
            ("dual_connection_color", tr("Dual color:")),
            ("reverse_connection_color", tr("Reverse color:")),
        ),
    ),
    (
        tr("Markers"),
        (
            ("marker_size", tr("Icon height (m):"), 0.1, 100.0, 0.5),
            ("marker_min_px", tr("Smallest on screen (px):"), 1.0, 200.0, 1.0),
            ("marker_max_px", tr("Largest on screen (px):"), 1.0, 200.0, 1.0),
            ("marker_name_min_zoom", tr("Names from zoom:"), 0.0, 50.0, 0.1),
        ),
        (),
    ),
)


class DisplayOptionsDialog(QDialog):
    """Dialog for editing the DisplayStyle."""

    style_applied = Signal(object)

    def __init__(self, display_style: DisplayStyle, parent=None):
        super().__init__(parent)

        self._base_style = display_style

        self.setWindowTitle(tr("Display options"))

        self.setMinimumWidth(500)

        self.resize(560, 720)

        self.size_inputs: dict[str, QDoubleSpinBox] = {}
        self.color_buttons: dict[str, ColorButton] = {}

        self._create_layout()
        self._load_style(display_style)

    def _create_layout(self):
        options_layout = QVBoxLayout()

        for title, sizes, colors in OPTION_GROUPS:
            group_layout = QFormLayout()

            for name, label, minimum, maximum, step in sizes:
                spin_box = self._create_spin_box(minimum, maximum, step, decimals=2)
                self.size_inputs[name] = spin_box
                group_layout.addRow(label, spin_box)

            for name, label in colors:
                button = ColorButton(getattr(DisplayStyle(), name))
                self.color_buttons[name] = button
                group_layout.addRow(label, button)

            group = QGroupBox(title)
            group.setLayout(group_layout)
            options_layout.addWidget(group)

        options_layout.addStretch(1)

        options_widget = QWidget()

        options_widget.setLayout(options_layout)

        scroll_area = QScrollArea()

        scroll_area.setWidgetResizable(True)

        scroll_area.setWidget(options_widget)

        self.default_button = QPushButton(tr("Defaults"))

        self.default_button.clicked.connect(self._load_defaults)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Apply | QDialogButtonBox.Cancel
        )

        self.button_box.accepted.connect(self._accept_changes)

        self.button_box.rejected.connect(self.reject)

        apply_button = self.button_box.button(QDialogButtonBox.Apply)

        apply_button.clicked.connect(self._apply_changes)

        bottom_layout = QHBoxLayout()

        bottom_layout.addWidget(self.default_button)

        bottom_layout.addStretch(1)

        bottom_layout.addWidget(self.button_box)

        main_layout = QVBoxLayout()

        main_layout.addWidget(scroll_area, 1)

        main_layout.addLayout(bottom_layout)

        self.setLayout(main_layout)

    def _load_style(self, display_style: DisplayStyle):
        for name, spin_box in self.size_inputs.items():
            spin_box.setValue(getattr(display_style, name))

        for name, button in self.color_buttons.items():
            button.set_color(getattr(display_style, name))

    def _build_style(self) -> DisplayStyle:
        sizes = {name: spin_box.value() for name, spin_box in self.size_inputs.items()}
        colors = {name: button.color for name, button in self.color_buttons.items()}

        return replace(self._base_style, **sizes, **colors)

    def _apply_changes(self):
        display_style = self._build_style()

        self._base_style = display_style

        self.style_applied.emit(display_style)

    def _accept_changes(self):
        self._apply_changes()
        self.accept()

    def _load_defaults(self):
        self._load_style(DisplayStyle())

    @staticmethod
    def _create_spin_box(
        minimum: float, maximum: float, step: float, decimals: int
    ) -> QDoubleSpinBox:
        spin_box = QDoubleSpinBox()

        spin_box.setRange(minimum, maximum)

        spin_box.setSingleStep(step)

        spin_box.setDecimals(decimals)

        spin_box.setKeyboardTracking(False)

        return spin_box
