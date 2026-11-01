from PySide6.QtCore import QSize
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QStackedWidget, QToolButton, QWidget

from autodrive_editor.ui.actions.tool_catalog import merged_tool_of
from autodrive_editor.ui.tools.interaction_mode import InteractionMode


class OptionsBar(QFrame):
    """The bar above the map: the active tool's name, its variant buttons, then its options.
    The bar keeps the height of its tallest options, so the map does not move when the tool
    changes."""

    VARIANT_ICON_SIZE = QSize(24, 24)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setFrameShape(QFrame.StyledPanel)
        self.name_label = QLabel(self)
        self.name_label.setStyleSheet("font-weight: bold;")
        self.stack = QStackedWidget(self)
        self.no_options = QWidget(self.stack)
        self.stack.addWidget(self.no_options)
        self.options: dict[InteractionMode, QWidget] = {}
        self.variants: dict[InteractionMode, QWidget] = {}

        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(6, 2, 6, 2)
        self._layout.setSpacing(12)
        self._layout.addWidget(self.name_label)
        self._layout.addWidget(self.stack, 1)

    def add_options(self, modes, widget: QWidget):
        """Shows the widget while one of the modes is active."""

        self.stack.addWidget(widget)

        for mode in modes:
            self.options[mode] = widget

    def add_variants(self, actions: dict[InteractionMode, QAction]):
        """Shows a button per variant action while one of the variants is active."""

        widget = QWidget(self)
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        for action in actions.values():
            button = QToolButton(widget)
            button.setDefaultAction(action)
            button.setIconSize(self.VARIANT_ICON_SIZE)
            button.setAutoRaise(True)
            layout.addWidget(button)

        widget.hide()
        self._layout.insertWidget(self._layout.indexOf(self.stack), widget)

        for mode in actions:
            self.variants[mode] = widget

    def show_tool(self, mode: InteractionMode):
        tool = merged_tool_of(mode)
        self.name_label.setText(mode.display_name if tool is None else tool.text)
        self.stack.setCurrentWidget(self.options.get(mode, self.no_options))

        for widget in set(self.variants.values()):
            widget.setVisible(widget is self.variants.get(mode))
