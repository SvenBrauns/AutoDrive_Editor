from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QStackedWidget, QWidget

from autodrive_editor.ui.tools.interaction_mode import InteractionMode


class OptionsBar(QFrame):
    """The bar above the map: the active tool's name, then its options. The bar keeps the
    height of its tallest options, so the map does not move when the tool changes."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setFrameShape(QFrame.StyledPanel)
        self.name_label = QLabel(self)
        self.name_label.setStyleSheet("font-weight: bold;")
        self.stack = QStackedWidget(self)
        self.no_options = QWidget(self.stack)
        self.stack.addWidget(self.no_options)
        self.options: dict[InteractionMode, QWidget] = {}

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 2, 6, 2)
        layout.setSpacing(12)
        layout.addWidget(self.name_label)
        layout.addWidget(self.stack, 1)

    def add_options(self, modes, widget: QWidget):
        """Shows the widget while one of the modes is active."""

        self.stack.addWidget(widget)

        for mode in modes:
            self.options[mode] = widget

    def show_tool(self, mode: InteractionMode):
        self.name_label.setText(mode.display_name)
        self.stack.setCurrentWidget(self.options.get(mode, self.no_options))
