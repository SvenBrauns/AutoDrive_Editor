from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDockWidget, QLabel, QVBoxLayout, QWidget

from autodrive_editor.i18n import tr


class InspectorDock(QDockWidget):
    """Details of the selected node: number, position, type, connections, marker, heights."""

    def __init__(self, parent=None):
        super().__init__(tr("Inspector"), parent)

        self.setObjectName("inspector_dock")
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.setFeatures(
            QDockWidget.DockWidgetClosable
            | QDockWidget.DockWidgetMovable
            | QDockWidget.DockWidgetFloatable
        )

        self.node_info_value = QLabel()
        self.node_info_value.setWordWrap(True)
        self.node_info_value.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.node_info_value.setAlignment(Qt.AlignTop)
        self.set_node_info(None)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.addWidget(self.node_info_value)
        layout.addStretch(1)
        self.setWidget(content)

    def set_node_info(self, node_info_text: str | None):
        self.node_info_value.setText(node_info_text or tr("Nothing selected"))
