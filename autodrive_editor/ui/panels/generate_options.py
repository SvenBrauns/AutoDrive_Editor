from PySide6.QtCore import QSize, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QToolButton,
    QWidget,
)

from autodrive_editor.editing.junctions.junction import Stem
from autodrive_editor.editing.junctions.junction_box import Style
from autodrive_editor.editing.operations.road_network import RoadLanes, RoadMode, RoadSettings
from autodrive_editor.i18n import tr
from autodrive_editor.ui.tools.generate_tool import GenerateTask


class GenerateOptionsWidget(QWidget):
    """The task buttons of the Generate tool in the options bar, the Route task's waypoint buttons,
    the Junction task's options and the Roads task's options, each shown only for its task."""

    TASK_ICON_SIZE = QSize(24, 24)

    # The Junction task's stem kind and lane gap.
    stem_changed = Signal(object, float)
    # The Junction task's style (see Style).
    style_changed = Signal(object)
    # The Route task's buttons.
    remove_last_requested = Signal()
    clear_requested = Signal()
    # The Roads task's settings (RoadSettings) and its Create button (whole map).
    road_settings_changed = Signal(object)
    create_roads_requested = Signal()

    def __init__(
        self,
        task_actions: dict[GenerateTask, QAction],
        task: GenerateTask,
        stem: Stem,
        gap: float,
        style: Style = Style.BOX,
        roads: RoadSettings | None = None,
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
            (Stem.IN_ONLY, tr("One way in")),
            (Stem.OUT_ONLY, tr("One way out")),
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

        self.route_options = QWidget(self)
        route_row = QHBoxLayout(self.route_options)
        route_row.setContentsMargins(0, 0, 0, 0)
        self.remove_last_button = QPushButton(tr("Remove last (Backspace)"), self.route_options)
        self.remove_last_button.clicked.connect(self.remove_last_requested)
        self.clear_button = QPushButton(tr("Clear (Esc)"), self.route_options)
        self.clear_button.clicked.connect(self.clear_requested)
        route_row.addWidget(self.remove_last_button)
        route_row.addWidget(self.clear_button)

        layout.addSpacing(8)
        layout.addWidget(self.route_options)
        roads = roads or RoadSettings()
        self.road_options = QWidget(self)
        road_row = QHBoxLayout(self.road_options)
        road_row.setContentsMargins(0, 0, 0, 0)
        self.road_mode_box = self._choices(
            (
                (RoadMode.BOX, tr("Box")),
                (RoadMode.WHOLE_MAP, tr("Whole map")),
                (RoadMode.CLICK_ROAD, tr("Click road")),
            ),
            roads.mode,
            tr("Box: right-drag a box; Whole map: Create; Click road: from junction to junction"),
        )
        self.road_existing_box = self._choices(
            ((False, tr("Skip and connect")), (True, tr("Replace"))),
            roads.replace,
            tr("Roads already in the network: leave them and connect to them, or replace them"),
        )
        self.road_lanes_box = self._choices(
            (
                (RoadLanes.AUTO, tr("Auto")),
                (RoadLanes.PAIRS, tr("Two one-way")),
                (RoadLanes.TWO_WAY, tr("Two-way")),
            ),
            roads.lanes,
            tr("Auto: as most of the existing network; the lane gap is the Junction task's"),
        )
        self.create_roads_button = QPushButton(tr("Create"), self.road_options)
        self.create_roads_button.setToolTip(tr("Build the roads of the whole map"))
        self.create_roads_button.clicked.connect(self.create_roads_requested)

        for title, widget in (
            (tr("Mode:"), self.road_mode_box),
            (tr("Existing:"), self.road_existing_box),
            (tr("Lanes:"), self.road_lanes_box),
        ):
            road_row.addWidget(QLabel(title, self.road_options))
            road_row.addWidget(widget)
            widget.currentIndexChanged.connect(self._emit_road_settings)

        road_row.addWidget(self.create_roads_button)

        layout.addSpacing(8)
        layout.addWidget(self.junction_options)
        layout.addSpacing(8)
        layout.addWidget(self.road_options)
        layout.addStretch(1)
        self.set_task(task)
        self._update_create_button()

    @property
    def road_settings(self) -> RoadSettings:
        return RoadSettings(
            self.road_mode_box.currentData(),
            self.road_existing_box.currentData(),
            self.road_lanes_box.currentData(),
        )

    def set_task(self, task: GenerateTask):
        self.junction_options.setHidden(task != GenerateTask.JUNCTION)
        self.route_options.setHidden(task != GenerateTask.ROUTE)
        self.road_options.setHidden(task != GenerateTask.ROADS)

    def _choices(self, items, current, tool_tip: str) -> QComboBox:
        box = QComboBox(self.road_options)
        box.setToolTip(tool_tip)

        for value, name in items:
            box.addItem(name, value)

        box.setCurrentIndex(box.findData(current))
        return box

    def _emit_road_settings(self):
        self._update_create_button()
        self.road_settings_changed.emit(self.road_settings)

    def _update_create_button(self):
        self.create_roads_button.setEnabled(self.road_mode_box.currentData() == RoadMode.WHOLE_MAP)

    def _emit_stem(self):
        self.stem_changed.emit(self.stem_box.currentData(), self.gap_box.value())
