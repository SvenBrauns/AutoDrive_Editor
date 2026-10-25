from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDockWidget, QFormLayout, QGroupBox, QLabel, QVBoxLayout, QWidget

from autodrive_editor.ui.tools.interaction_mode import InteractionMode


class DebugDock(QDockWidget):
    EMPTY_VALUE = "-"

    def __init__(self, parent=None):
        super().__init__("Debuganzeige", parent)

        self.setObjectName("debug_dock")

        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)

        self.setFeatures(
            QDockWidget.DockWidgetClosable
            | QDockWidget.DockWidgetMovable
            | QDockWidget.DockWidgetFloatable
        )

        self.setMinimumWidth(280)

        self._create_content()

    def _create_content(self):
        self.interaction_mode_value = QLabel(self.EMPTY_VALUE)

        self.zoom_value = QLabel(self.EMPTY_VALUE)

        self.rotation_value = QLabel(self.EMPTY_VALUE)

        self.visible_rect_value = QLabel(self.EMPTY_VALUE)

        self.total_nodes_value = QLabel("0")

        self.visible_nodes_value = QLabel("0")

        self.visible_markers_value = QLabel("0")

        self.selected_nodes_value = QLabel("0")

        self.visible_selection_items_value = QLabel("0")

        self.connection_mode_value = QLabel(self.EMPTY_VALUE)

        self.total_connections_value = QLabel("0")

        self.node_layer_value = QLabel(self.EMPTY_VALUE)

        self.marker_layer_value = QLabel(self.EMPTY_VALUE)

        self.node_info_value = QLabel("Keine Node ausgewählt")

        self.node_info_value.setWordWrap(True)

        self.node_info_value.setTextInteractionFlags(Qt.TextSelectableByMouse)

        self.node_info_value.setAlignment(Qt.AlignTop)

        form_layout = QFormLayout()

        form_layout.addRow("Interaktionsmodus:", self.interaction_mode_value)

        form_layout.addRow("Zoom:", self.zoom_value)

        form_layout.addRow("Rotation:", self.rotation_value)

        form_layout.addRow("Sichtbarer Bereich:", self.visible_rect_value)

        form_layout.addRow("Nodes insgesamt:", self.total_nodes_value)

        form_layout.addRow("Sichtbare Nodes:", self.visible_nodes_value)

        form_layout.addRow("Sichtbare Marker:", self.visible_markers_value)

        form_layout.addRow("Ausgewählte Nodes:", self.selected_nodes_value)

        form_layout.addRow("Sichtbare Auswahlringe:", self.visible_selection_items_value)

        form_layout.addRow("Connection-Modus:", self.connection_mode_value)

        form_layout.addRow("Connections insgesamt:", self.total_connections_value)

        form_layout.addRow("Node-Layer:", self.node_layer_value)

        form_layout.addRow("Marker-Layer:", self.marker_layer_value)

        runtime_group = QGroupBox("Laufzeit")

        runtime_group.setLayout(form_layout)

        selection_layout = QVBoxLayout()

        selection_layout.addWidget(self.node_info_value)

        selection_group = QGroupBox("Auswahl")

        selection_group.setLayout(selection_layout)

        content_layout = QVBoxLayout()

        content_layout.addWidget(runtime_group)

        content_layout.addWidget(selection_group)

        content_layout.addStretch(1)

        content_widget = QWidget()

        content_widget.setLayout(content_layout)

        self.setWidget(content_widget)

    def set_interaction_mode(self, interaction_mode: InteractionMode):
        self.interaction_mode_value.setText(interaction_mode.display_name)

    def set_view_state(self, zoom_level: float, rotation_angle: float, visible_rect):
        self.zoom_value.setText(f"{zoom_level:.4f}")

        self.rotation_value.setText(f"{rotation_angle:.2f}°")

        if visible_rect is None:
            self.visible_rect_value.setText(self.EMPTY_VALUE)
            return

        self.visible_rect_value.setText(
            f"X {visible_rect.left():.1f} bis "
            f"{visible_rect.right():.1f}\n"
            f"Z {visible_rect.top():.1f} bis "
            f"{visible_rect.bottom():.1f}"
        )

    def set_renderer_state(self, debug_state: dict):
        self.total_nodes_value.setText(str(debug_state["total_nodes"]))

        self.visible_nodes_value.setText(str(debug_state["visible_nodes"]))

        self.visible_markers_value.setText(str(debug_state["visible_markers"]))

        self.selected_nodes_value.setText(str(debug_state["selected_nodes"]))

        self.visible_selection_items_value.setText(str(debug_state["visible_selection_items"]))

        self.connection_mode_value.setText(debug_state["connection_mode"])

        self.total_connections_value.setText(str(debug_state["total_connections"]))

        self.node_layer_value.setText(self._format_visibility(debug_state["nodes_visible"]))

        self.marker_layer_value.setText(self._format_visibility(debug_state["markers_visible"]))

    def set_node_info(self, node_info_text: str | None):
        if not node_info_text:
            node_info_text = "Keine Node ausgewählt"

        self.node_info_value.setText(node_info_text)

    @classmethod
    def _format_visibility(cls, visible) -> str:
        if visible is True:
            return "sichtbar"

        if visible is False:
            return "ausgeblendet"

        return cls.EMPTY_VALUE
