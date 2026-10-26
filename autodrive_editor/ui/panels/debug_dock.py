from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDockWidget, QFormLayout, QGroupBox, QLabel, QVBoxLayout, QWidget

from autodrive_editor.i18n import tr
from autodrive_editor.ui.tools.interaction_mode import InteractionMode


class DebugDock(QDockWidget):
    """Dock with view, renderer and selection details for debugging."""

    EMPTY_VALUE = "-"

    def __init__(self, parent=None):
        super().__init__(tr("Debug info"), parent)

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

        self.total_connections_value = QLabel("0")

        self.selected_nodes_value = QLabel("0")

        self.drawn_markers_value = QLabel("0")

        self.drawn_arrows_value = QLabel("0")

        self.cached_tiles_value = QLabel("0")

        self.node_info_value = QLabel(tr("No node selected"))

        self.node_info_value.setWordWrap(True)

        self.node_info_value.setTextInteractionFlags(Qt.TextSelectableByMouse)

        self.node_info_value.setAlignment(Qt.AlignTop)

        form_layout = QFormLayout()

        form_layout.addRow(tr("Interaction mode:"), self.interaction_mode_value)

        form_layout.addRow("Zoom:", self.zoom_value)

        form_layout.addRow(tr("Rotation:"), self.rotation_value)

        form_layout.addRow(tr("Visible area:"), self.visible_rect_value)

        form_layout.addRow(tr("Total nodes:"), self.total_nodes_value)

        form_layout.addRow(tr("Total connections:"), self.total_connections_value)

        form_layout.addRow(tr("Selected nodes:"), self.selected_nodes_value)

        form_layout.addRow(tr("Visible markers:"), self.drawn_markers_value)

        form_layout.addRow(tr("Drawn arrows:"), self.drawn_arrows_value)

        form_layout.addRow(tr("Cached map tiles:"), self.cached_tiles_value)

        runtime_group = QGroupBox(tr("Runtime"))

        runtime_group.setLayout(form_layout)

        selection_layout = QVBoxLayout()

        selection_layout.addWidget(self.node_info_value)

        selection_group = QGroupBox(tr("Selection"))

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
            tr(
                "X {left:.1f} to {right:.1f}\nZ {top:.1f} to {bottom:.1f}",
                left=visible_rect.left(),
                right=visible_rect.right(),
                top=visible_rect.top(),
                bottom=visible_rect.bottom(),
            )
        )

    def set_renderer_state(self, debug_state: dict):
        self.total_nodes_value.setText(str(debug_state["total_nodes"]))

        self.total_connections_value.setText(str(debug_state["total_connections"]))

        self.selected_nodes_value.setText(str(debug_state["selected_nodes"]))

        self.drawn_markers_value.setText(str(debug_state["drawn_markers"]))

        self.drawn_arrows_value.setText(str(debug_state["drawn_arrows"]))

        self.cached_tiles_value.setText(str(debug_state["cached_tiles"]))

    def set_node_info(self, node_info_text: str | None):
        if not node_info_text:
            node_info_text = tr("No node selected")

        self.node_info_value.setText(node_info_text)
