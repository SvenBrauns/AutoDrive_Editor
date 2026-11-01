from PySide6.QtCore import QSize, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QComboBox, QDoubleSpinBox, QHBoxLayout, QLabel, QToolButton, QWidget

from autodrive_editor.editing.junction import Stem
from autodrive_editor.editing.junction_box import Style
from autodrive_editor.i18n import tr
from autodrive_editor.ui.tools.generate_tool import GenerateTask


class GenerateOptionsWidget(QWidget):
    """The task buttons of the Generate tool in the options bar, and the Junction task's options,
    enabled only for that task."""

    TASK_ICON_SIZE = QSize(24, 24)

    # The Junction task's stem kind and lane gap.
    stem_changed = Signal(object, float)
    # The Junction task's style (see Style).
    style_changed = Signal(object)

    def __init__(
        self,
        task_actions: dict[GenerateTask, QAction],
        task: GenerateTask,
        stem: Stem,
        gap: float,
        style: Style = Style.BOX,
        parent=None,
    ):
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        tasks = QHBoxLayout()
        tasks.setSpacing(2)
        layout.addLayout(tasks)
        self.task_buttons: dict[GenerateTask, QToolButton] = {}

        for each, action in task_actions.items():
            button = QToolButton(self)
            button.setDefaultAction(action)
            button.setIconSize(self.TASK_ICON_SIZE)
            button.setAutoRaise(True)
            self.task_buttons[each] = button
            tasks.addWidget(button)

        self.junction_options = QWidget(self)
        self.style_box = QComboBox(self.junction_options)
        self.style_box.setToolTip(
            tr("Box: a box where two lanes cross two lanes, otherwise turn curves")
        )

        for each, name in ((Style.BOX, tr("Box")), (Style.CURVES, tr("Curves"))):
            self.style_box.addItem(name, each)

        self.style_box.setCurrentIndex(self.style_box.findData(style))
        self.style_box.currentIndexChanged.connect(
            lambda: self.style_changed.emit(self.style_box.currentData())
        )
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

        row = QHBoxLayout(self.junction_options)
        row.setContentsMargins(0, 0, 0, 0)

        for title, widget in (
            (tr("Style:"), self.style_box),
            (tr("Stem:"), self.stem_box),
            (tr("Lane gap:"), self.gap_box),
        ):
            row.addWidget(QLabel(title, self.junction_options))
            row.addWidget(widget)

        layout.addSpacing(8)
        layout.addWidget(self.junction_options)
        layout.addStretch(1)
        self.junction_options.setEnabled(task == GenerateTask.JUNCTION)

    def set_task(self, task: GenerateTask):
        self.junction_options.setEnabled(task == GenerateTask.JUNCTION)

    def _emit_stem(self):
        self.stem_changed.emit(self.stem_box.currentData(), self.gap_box.value())
