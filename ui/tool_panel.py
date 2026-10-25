from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QDockWidget,
    QGroupBox,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget
)


class ToolPanel(QDockWidget):
    """Left dock with one box per tool group, e.g. "Nodes" or
    "Marker". Each tool is a checkable action shown as a button."""

    def __init__(
        self,
        parent=None
    ):
        super().__init__(
            "Werkzeuge",
            parent
        )

        self.setObjectName(
            "tool_panel"
        )

        self.setAllowedAreas(
            Qt.LeftDockWidgetArea
            | Qt.RightDockWidgetArea
        )

        self.setFeatures(
            QDockWidget.DockWidgetClosable
            | QDockWidget.DockWidgetMovable
        )

        content = QWidget(
            self
        )

        self._layout = QVBoxLayout(
            content
        )

        self._layout.setContentsMargins(
            6,
            6,
            6,
            6
        )

        self._layout.addStretch(
            1
        )

        self.setWidget(
            content
        )

        self.tool_buttons: dict[QAction, QToolButton] = {}

    def add_tool_group(
        self,
        title: str,
        actions: list[QAction]
    ) -> QGroupBox:
        group_box = QGroupBox(
            title,
            self.widget()
        )

        group_layout = QVBoxLayout(
            group_box
        )

        group_layout.setContentsMargins(
            4,
            4,
            4,
            4
        )

        for action in actions:
            button = QToolButton(
                group_box
            )

            button.setDefaultAction(
                action
            )

            button.setToolButtonStyle(
                Qt.ToolButtonTextOnly
            )

            button.setSizePolicy(
                QSizePolicy.Expanding,
                QSizePolicy.Fixed
            )

            group_layout.addWidget(
                button
            )

            self.tool_buttons[
                action
            ] = button

        # Keep the stretch at the end so groups stack at the top.
        self._layout.insertWidget(
            self._layout.count() - 1,
            group_box
        )

        return group_box
