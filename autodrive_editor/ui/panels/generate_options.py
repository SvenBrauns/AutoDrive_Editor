from PySide6.QtCore import Signal
from PySide6.QtWidgets import QButtonGroup, QRadioButton, QVBoxLayout, QWidget

from autodrive_editor.ui.tools.generate_tool import GenerateTask


class GenerateOptionsWidget(QWidget):
    """What the Generate tool creates, shown from the arrow of its button."""

    task_changed = Signal(object)

    def __init__(self, task: GenerateTask, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        self.buttons = QButtonGroup(self)
        self.task_buttons: dict[GenerateTask, QRadioButton] = {}

        for each in GenerateTask:
            button = QRadioButton(each.display_name, self)
            button.setChecked(each == task)
            button.toggled.connect(
                lambda checked, each=each: checked and self.task_changed.emit(each)
            )
            self.buttons.addButton(button)
            self.task_buttons[each] = button
            layout.addWidget(button)
