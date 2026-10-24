from dataclasses import replace

from PySide6.QtCore import Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
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
    QColorDialog
)

from rendering.display_style import DisplayStyle


class ColorButton(QPushButton):

    color_changed = Signal(
        tuple
    )

    def __init__(
        self,
        color: tuple[int, int, int],
        parent=None
    ):
        super().__init__(
            parent
        )

        self._color = color

        self.clicked.connect(
            self._select_color
        )

        self._update_appearance()

    @property
    def color(
        self
    ) -> tuple[int, int, int]:
        return self._color

    def set_color(
        self,
        color: tuple[int, int, int]
    ):
        self._color = (
            int(color[0]),
            int(color[1]),
            int(color[2])
        )

        self._update_appearance()

    def _select_color(self):
        initial_color = QColor(
            self._color[0],
            self._color[1],
            self._color[2]
        )

        selected_color = QColorDialog.getColor(
            initial_color,
            self,
            "Farbe auswählen"
        )

        if not selected_color.isValid():
            return

        self.set_color(
            (
                selected_color.red(),
                selected_color.green(),
                selected_color.blue()
            )
        )

        self.color_changed.emit(
            self._color
        )

    def _update_appearance(self):
        red, green, blue = self._color

        brightness = (
            red * 0.299
            + green * 0.587
            + blue * 0.114
        )

        text_color = (
            "black"
            if brightness >= 150
            else "white"
        )

        self.setText(
            f"RGB {red}, {green}, {blue}"
        )

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


class DisplayOptionsDialog(QDialog):

    style_applied = Signal(
        object
    )

    def __init__(
        self,
        display_style: DisplayStyle,
        parent=None
    ):
        super().__init__(
            parent
        )

        self._base_style = display_style

        self.setWindowTitle(
            "Darstellungsoptionen"
        )

        self.setMinimumWidth(
            500
        )

        self.resize(
            560,
            720
        )

        self._create_controls()
        self._create_layout()
        self._load_style(
            display_style
        )

    def _create_controls(self):
        self.node_diameter_input = (
            self._create_spin_box(
                minimum=0.1,
                maximum=100.0,
                step=0.1,
                decimals=2
            )
        )

        self.node_border_width_input = (
            self._create_spin_box(
                minimum=0.0,
                maximum=20.0,
                step=0.05,
                decimals=2
            )
        )

        self.selected_node_ring_width_input = (
            self._create_spin_box(
                minimum=0.0,
                maximum=20.0,
                step=0.05,
                decimals=2
            )
        )

        self.marker_scale_input = (
            self._create_spin_box(
                minimum=0.001,
                maximum=10.0,
                step=0.01,
                decimals=3
            )
        )

        self.marker_node_gap_input = (
            self._create_spin_box(
                minimum=0.0,
                maximum=100.0,
                step=0.1,
                decimals=2
            )
        )

        self.connection_width_input = (
            self._create_spin_box(
                minimum=0.01,
                maximum=20.0,
                step=0.05,
                decimals=2
            )
        )

        self.detailed_connection_width_input = (
            self._create_spin_box(
                minimum=0.01,
                maximum=20.0,
                step=0.05,
                decimals=2
            )
        )

        self.arrow_length_input = (
            self._create_spin_box(
                minimum=0.01,
                maximum=100.0,
                step=0.1,
                decimals=2
            )
        )

        self.arrow_width_input = (
            self._create_spin_box(
                minimum=0.01,
                maximum=100.0,
                step=0.1,
                decimals=2
            )
        )

        self.node_min_zoom_input = (
            self._create_spin_box(
                minimum=0.0,
                maximum=50.0,
                step=0.1,
                decimals=3
            )
        )

        self.marker_min_zoom_input = (
            self._create_spin_box(
                minimum=0.0,
                maximum=50.0,
                step=0.1,
                decimals=3
            )
        )

        self.connection_detail_min_zoom_input = (
            self._create_spin_box(
                minimum=0.0,
                maximum=50.0,
                step=0.1,
                decimals=3
            )
        )

        default_style = DisplayStyle()

        self.regular_connection_color_button = (
            ColorButton(
                default_style.regular_connection_color
            )
        )

        self.dual_connection_color_button = (
            ColorButton(
                default_style.dual_connection_color
            )
        )

        self.reverse_connection_color_button = (
            ColorButton(
                default_style.reverse_connection_color
            )
        )

    def _create_layout(self):
        node_layout = QFormLayout()

        node_layout.addRow(
            "Node-Durchmesser:",
            self.node_diameter_input
        )

        node_layout.addRow(
            "Node-Randbreite:",
            self.node_border_width_input
        )

        node_layout.addRow(
            "Auswahlring-Breite:",
            self.selected_node_ring_width_input
        )

        node_group = QGroupBox(
            "Nodes"
        )

        node_group.setLayout(
            node_layout
        )

        marker_layout = QFormLayout()

        marker_layout.addRow(
            "Marker-Skalierung:",
            self.marker_scale_input
        )

        marker_layout.addRow(
            "Abstand zur Node:",
            self.marker_node_gap_input
        )

        marker_group = QGroupBox(
            "Marker"
        )

        marker_group.setLayout(
            marker_layout
        )

        connection_layout = QFormLayout()

        connection_layout.addRow(
            "Übersichtsbreite:",
            self.connection_width_input
        )

        connection_layout.addRow(
            "Detailbreite:",
            self.detailed_connection_width_input
        )

        connection_layout.addRow(
            "Pfeillänge:",
            self.arrow_length_input
        )

        connection_layout.addRow(
            "Pfeilbreite:",
            self.arrow_width_input
        )

        connection_layout.addRow(
            "Regular-Farbe:",
            self.regular_connection_color_button
        )

        connection_layout.addRow(
            "Dual-Farbe:",
            self.dual_connection_color_button
        )

        connection_layout.addRow(
            "Reverse-Farbe:",
            self.reverse_connection_color_button
        )

        connection_group = QGroupBox(
            "Connections"
        )

        connection_group.setLayout(
            connection_layout
        )

        zoom_layout = QFormLayout()

        zoom_layout.addRow(
            "Nodes ab Zoom:",
            self.node_min_zoom_input
        )

        zoom_layout.addRow(
            "Marker ab Zoom:",
            self.marker_min_zoom_input
        )

        zoom_layout.addRow(
            "Detail-Connections ab Zoom:",
            self.connection_detail_min_zoom_input
        )

        zoom_group = QGroupBox(
            "Sichtbarkeitsgrenzen"
        )

        zoom_group.setLayout(
            zoom_layout
        )

        options_layout = QVBoxLayout()

        options_layout.addWidget(
            node_group
        )

        options_layout.addWidget(
            marker_group
        )

        options_layout.addWidget(
            connection_group
        )

        options_layout.addWidget(
            zoom_group
        )

        options_layout.addStretch(
            1
        )

        options_widget = QWidget()

        options_widget.setLayout(
            options_layout
        )

        scroll_area = QScrollArea()

        scroll_area.setWidgetResizable(
            True
        )

        scroll_area.setWidget(
            options_widget
        )

        self.default_button = QPushButton(
            "Standardwerte"
        )

        self.default_button.clicked.connect(
            self._load_defaults
        )

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.Ok
            | QDialogButtonBox.Apply
            | QDialogButtonBox.Cancel
        )

        self.button_box.accepted.connect(
            self._accept_changes
        )

        self.button_box.rejected.connect(
            self.reject
        )

        apply_button = self.button_box.button(
            QDialogButtonBox.Apply
        )

        apply_button.clicked.connect(
            self._apply_changes
        )

        bottom_layout = QHBoxLayout()

        bottom_layout.addWidget(
            self.default_button
        )

        bottom_layout.addStretch(
            1
        )

        bottom_layout.addWidget(
            self.button_box
        )

        main_layout = QVBoxLayout()

        main_layout.addWidget(
            scroll_area,
            1
        )

        main_layout.addLayout(
            bottom_layout
        )

        self.setLayout(
            main_layout
        )

    def _load_style(
        self,
        display_style: DisplayStyle
    ):
        self.node_diameter_input.setValue(
            display_style.node_diameter
        )

        self.node_border_width_input.setValue(
            display_style.node_border_width
        )

        self.selected_node_ring_width_input.setValue(
            display_style.selected_node_ring_width
        )

        self.marker_scale_input.setValue(
            display_style.marker_scale
        )

        self.marker_node_gap_input.setValue(
            display_style.marker_node_gap
        )

        self.connection_width_input.setValue(
            display_style.connection_width
        )

        self.detailed_connection_width_input.setValue(
            display_style.detailed_connection_width
        )

        self.arrow_length_input.setValue(
            display_style.arrow_length
        )

        self.arrow_width_input.setValue(
            display_style.arrow_width
        )

        self.node_min_zoom_input.setValue(
            display_style.node_min_zoom
        )

        self.marker_min_zoom_input.setValue(
            display_style.marker_min_zoom
        )

        self.connection_detail_min_zoom_input.setValue(
            display_style.connection_detail_min_zoom
        )

        self.regular_connection_color_button.set_color(
            display_style.regular_connection_color
        )

        self.dual_connection_color_button.set_color(
            display_style.dual_connection_color
        )

        self.reverse_connection_color_button.set_color(
            display_style.reverse_connection_color
        )

    def _build_style(self) -> DisplayStyle:
        return replace(
            self._base_style,
            node_diameter=(
                self.node_diameter_input.value()
            ),
            node_border_width=(
                self.node_border_width_input.value()
            ),
            selected_node_ring_width=(
                self.selected_node_ring_width_input.value()
            ),
            marker_scale=(
                self.marker_scale_input.value()
            ),
            marker_node_gap=(
                self.marker_node_gap_input.value()
            ),
            connection_width=(
                self.connection_width_input.value()
            ),
            detailed_connection_width=(
                self.detailed_connection_width_input.value()
            ),
            arrow_length=(
                self.arrow_length_input.value()
            ),
            arrow_width=(
                self.arrow_width_input.value()
            ),
            node_min_zoom=(
                self.node_min_zoom_input.value()
            ),
            marker_min_zoom=(
                self.marker_min_zoom_input.value()
            ),
            connection_detail_min_zoom=(
                self.connection_detail_min_zoom_input.value()
            ),
            regular_connection_color=(
                self.regular_connection_color_button.color
            ),
            dual_connection_color=(
                self.dual_connection_color_button.color
            ),
            reverse_connection_color=(
                self.reverse_connection_color_button.color
            )
        )

    def _apply_changes(self):
        display_style = self._build_style()

        self._base_style = display_style

        self.style_applied.emit(
            display_style
        )

    def _accept_changes(self):
        self._apply_changes()
        self.accept()

    def _load_defaults(self):
        self._load_style(
            DisplayStyle()
        )

    @staticmethod
    def _create_spin_box(
        minimum: float,
        maximum: float,
        step: float,
        decimals: int
    ) -> QDoubleSpinBox:
        spin_box = QDoubleSpinBox()

        spin_box.setRange(
            minimum,
            maximum
        )

        spin_box.setSingleStep(
            step
        )

        spin_box.setDecimals(
            decimals
        )

        spin_box.setKeyboardTracking(
            False
        )

        return spin_box