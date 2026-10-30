from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from autodrive_editor.editing.junction import Stem
from autodrive_editor.i18n import tr
from autodrive_editor.ui.tools.generate_tool import GenerateTask


class GenerateOptionsWidget(QWidget):
    """What the Generate tool creates, shown from the arrow of its button, and the options of
    the chosen task."""

    task_changed = Signal(object)
    # The Junction task's stem kind and lane gap.
    stem_changed = Signal(object, float)

    def __init__(self, task: GenerateTask, stem: Stem, gap: float, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        self.buttons = QButtonGroup(self)
        self.task_buttons: dict[GenerateTask, QRadioButton] = {}

        for each in GenerateTask:
            button = QRadioButton(each.display_name, self)
            button.setChecked(each == task)
            button.toggled.connect(lambda checked, each=each: checked and self._set_task(each))
            self.buttons.addButton(button)
            self.task_buttons[each] = button
            layout.addWidget(button)

        self.junction_options = QWidget(self)
        self.stem_box = QComboBox(self.junction_options)
        self.stem_box.setToolTip(
            tr("Auto: two lanes on a road of two one-way lanes, two-way on a two-way road")
        )

        for each, name in (
            (Stem.AUTO, tr("Auto")),
            (Stem.TWO_WAY, tr("Two-way")),
            (Stem.TWO_LANES, tr("Two lanes")),
        ):
            self.stem_box.addItem(name, each)

        self.stem_box.setCurrentIndex(self.stem_box.findData(stem))
        self.gap_box = QDoubleSpinBox(self.junction_options)
        self.gap_box.setRange(2.0, 20.0)
        self.gap_box.setDecimals(1)
        self.gap_box.setSingleStep(0.5)
        self.gap_box.setSuffix(" m")
        self.gap_box.setToolTip(tr("Distance between the two lanes of the stem"))
        self.gap_box.setValue(gap)
        self.stem_box.currentIndexChanged.connect(self._emit_stem)
        self.gap_box.valueChanged.connect(self._emit_stem)

        form = QFormLayout(self.junction_options)
        form.setContentsMargins(0, 0, 0, 0)
        form.addRow(tr("Stem:"), self.stem_box)
        form.addRow(tr("Lane gap:"), self.gap_box)
        layout.addWidget(self.junction_options)
        self.junction_options.setVisible(task == GenerateTask.JUNCTION)

    def _set_task(self, task: GenerateTask):
        self.junction_options.setVisible(task == GenerateTask.JUNCTION)
        self.task_changed.emit(task)

    def _emit_stem(self):
        self.stem_changed.emit(self.stem_box.currentData(), self.gap_box.value())
