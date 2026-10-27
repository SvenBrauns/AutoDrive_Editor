from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QDockWidget,
    QDoubleSpinBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from autodrive_editor.i18n import tr
from autodrive_editor.network_check.checks import (
    ALL_CHECKS,
    HEIGHT,
    OUTSIDE,
    OVERLAP,
    CheckResults,
    problem_node_ids,
)


class CheckDock(QDockWidget):
    """Results of the network check, one group per kind of problem, and a
    group of ignored entries. Clicking an entry shows its nodes on the map;
    entries can be fixed, ignored or no longer ignored. Each check can be
    switched off."""

    check_requested = Signal()
    tolerances_changed = Signal(float, float)
    checks_changed = Signal(object)
    nodes_activated = Signal(list)
    fix_requested = Signal(object)
    ignore_requested = Signal(object)
    unignore_requested = Signal(object)

    # (kind, problem) of an entry, as in CheckResults.entries().
    ENTRY_ROLE = Qt.ItemDataRole.UserRole
    # True on the group of ignored entries and its entries.
    IGNORED_ROLE = Qt.ItemDataRole.UserRole + 1

    NOT_CHECKED_TEXT = tr("The network has not been checked yet")

    TITLES = {
        OVERLAP: tr("Overlapping nodes"),
        OUTSIDE: tr("Nodes outside the map"),
        HEIGHT: tr("Height differs from the terrain"),
    }

    def __init__(self, overlap_tolerance: float, max_height_difference: float, parent=None):
        super().__init__(tr("Network check"), parent)

        self.setObjectName("check_dock")
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)

        self.check_boxes = {
            OVERLAP: QCheckBox(tr("Overlapping nodes within"), self),
            OUTSIDE: QCheckBox(tr("Nodes outside the map"), self),
            HEIGHT: QCheckBox(tr("Height differs by more than"), self),
        }

        for check_box in self.check_boxes.values():
            check_box.setChecked(True)
            check_box.toggled.connect(lambda _: self.checks_changed.emit(self.enabled_checks))

        self.overlap_box = QDoubleSpinBox(self)
        self.overlap_box.setRange(0.01, 10.0)
        self.overlap_box.setSingleStep(0.05)
        self.overlap_box.setSuffix(" m")
        self.overlap_box.setValue(overlap_tolerance)
        self.overlap_box.setToolTip(tr("Nodes closer to each other than this count as overlapping"))

        self.height_box = QDoubleSpinBox(self)
        self.height_box.setDecimals(1)
        self.height_box.setRange(0.1, 100.0)
        self.height_box.setSuffix(" m")
        self.height_box.setValue(max_height_difference)
        self.height_box.setToolTip(tr("Nodes further above or below the terrain are reported"))

        for box in (self.overlap_box, self.height_box):
            box.valueChanged.connect(
                lambda _: self.tolerances_changed.emit(
                    self.overlap_box.value(), self.height_box.value()
                )
            )

        options = QGridLayout()
        options.addWidget(self.check_boxes[OVERLAP], 0, 0)
        options.addWidget(self.overlap_box, 0, 1)
        options.addWidget(self.check_boxes[OUTSIDE], 1, 0)
        options.addWidget(self.check_boxes[HEIGHT], 2, 0)
        options.addWidget(self.height_box, 2, 1)

        self.check_button = QPushButton(tr("Check network"), self)
        self.check_button.clicked.connect(self.check_requested)

        self.summary = QLabel(self.NOT_CHECKED_TEXT, self)
        self.summary.setWordWrap(True)

        self.tree = QTreeWidget(self)
        self.tree.setHeaderHidden(True)
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.tree.itemClicked.connect(self._handle_click)
        self.tree.itemSelectionChanged.connect(self._update_buttons)

        self.ignore_button = QPushButton(tr("Ignore"), self)
        self.ignore_button.setToolTip(tr("Don't report the selected entries again"))
        self.ignore_button.clicked.connect(
            lambda: self.ignore_requested.emit(self._results_of(self.tree.selectedItems()))
        )

        self.unignore_button = QPushButton(tr("Don't ignore"), self)
        self.unignore_button.setToolTip(tr("Report the selected ignored entries again"))
        self.unignore_button.clicked.connect(
            lambda: self.unignore_requested.emit(
                self._results_of(self.tree.selectedItems(), ignored=True)
            )
        )

        self.fix_selected_button = QPushButton(tr("Fix selected"), self)
        self.fix_selected_button.clicked.connect(
            lambda: self.fix_requested.emit(self._results_of(self.tree.selectedItems()))
        )

        self.fix_all_button = QPushButton(tr("Fix all"), self)
        self.fix_all_button.clicked.connect(
            lambda: self.fix_requested.emit(self._results_of(self._group_items()))
        )

        ignore_buttons = QHBoxLayout()
        ignore_buttons.addWidget(self.ignore_button)
        ignore_buttons.addWidget(self.unignore_button)

        fix_buttons = QHBoxLayout()
        fix_buttons.addWidget(self.fix_selected_button)
        fix_buttons.addWidget(self.fix_all_button)

        content = QWidget(self)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addLayout(options)
        layout.addWidget(self.check_button)
        layout.addWidget(self.summary)
        layout.addWidget(self.tree)
        layout.addLayout(ignore_buttons)
        layout.addLayout(fix_buttons)

        self.setWidget(content)
        self.set_results(None)

    @property
    def tolerances(self) -> tuple[float, float]:
        return self.overlap_box.value(), self.height_box.value()

    @property
    def enabled_checks(self) -> set[str]:
        return {kind for kind, check_box in self.check_boxes.items() if check_box.isChecked()}

    def set_enabled_checks(self, checks):
        """Ticks the boxes of the given checks without reporting a change."""

        for kind, check_box in self.check_boxes.items():
            check_box.blockSignals(True)
            check_box.setChecked(kind in checks)
            check_box.blockSignals(False)

    def set_results(self, results: CheckResults | None, ignored: CheckResults | None = None):
        """Shows the results and the ignored entries; None clears the list,
        e.g. for new data."""

        self.tree.clear()

        if results is None:
            self.summary.setText(self.NOT_CHECKED_TEXT)
        elif results.problem_count == 0:
            self.summary.setText(tr("No problems found"))
        else:
            self.summary.setText(tr("Problems found: {count}", count=results.problem_count))

        if results is not None:
            entries = results.entries()

            for kind in ALL_CHECKS:
                title = self.TITLES[kind]
                kind_entries = [entry for entry in entries if entry[0] == kind]

                if kind not in self.enabled_checks:
                    text = tr("{check}: switched off", check=title)
                elif kind == HEIGHT and results.height_problems is None:
                    text = tr("Heights not checked: no heightmap loaded")
                else:
                    text = f"{title} ({len(kind_entries)})"

                self._add_group(text, kind_entries)

        if ignored is not None and ignored.problem_count:
            group_item = self._add_group(
                tr("Ignored ({count})", count=ignored.problem_count), ignored.entries()
            )
            group_item.setExpanded(False)

            for item in [
                group_item,
                *(group_item.child(i) for i in range(group_item.childCount())),
            ]:
                item.setData(0, self.IGNORED_ROLE, True)

        self._update_buttons()

    def group_item(self, index: int) -> QTreeWidgetItem:
        """The group of overlapping nodes (0), outside the map (1), height
        differences (2) or ignored entries (3)."""

        return self.tree.topLevelItem(index)

    def _add_group(self, text: str, entries: list[tuple[str, object]]) -> QTreeWidgetItem:
        group_item = QTreeWidgetItem([text])
        self.tree.addTopLevelItem(group_item)

        for kind, problem in entries:
            entry_item = QTreeWidgetItem([self._entry_text(kind, problem)])
            entry_item.setData(0, self.ENTRY_ROLE, (kind, problem))
            group_item.addChild(entry_item)

        group_item.setExpanded(True)

        return group_item

    @staticmethod
    def _entry_text(kind: str, problem) -> str:
        if kind == OVERLAP:
            return tr("Nodes {nodes}", nodes=", ".join(map(str, problem)))

        if kind == OUTSIDE:
            return tr("Node {node}", node=problem)

        return tr(
            "Node {node}: {height:.1f} m, terrain {terrain:.1f} m",
            node=problem.node_id,
            height=problem.height,
            terrain=problem.terrain_height,
        )

    def _group_items(self) -> list[QTreeWidgetItem]:
        return [self.tree.topLevelItem(i) for i in range(self.tree.topLevelItemCount())]

    def _results_of(self, items: list[QTreeWidgetItem], ignored=False) -> CheckResults:
        """The problems of the given items that are ignored or not; a group
        item stands for all of its entries."""

        entries = []

        for item in items:
            if bool(item.data(0, self.IGNORED_ROLE)) != ignored:
                continue

            if item.data(0, self.ENTRY_ROLE) is not None:
                entries.append(item.data(0, self.ENTRY_ROLE))
            else:
                entries.extend(
                    item.child(i).data(0, self.ENTRY_ROLE) for i in range(item.childCount())
                )

        # A group and one of its entries may both be selected.
        return CheckResults.from_entries(entries)

    def _update_buttons(self):
        selected = self.tree.selectedItems()
        has_selected = self._results_of(selected).problem_count > 0

        self.fix_all_button.setEnabled(self._results_of(self._group_items()).problem_count > 0)
        self.fix_selected_button.setEnabled(has_selected)
        self.ignore_button.setEnabled(has_selected)
        self.unignore_button.setEnabled(self._results_of(selected, ignored=True).problem_count > 0)

    def _handle_click(self, item: QTreeWidgetItem, column: int):
        entry = item.data(0, self.ENTRY_ROLE)

        if entry is not None:
            self.nodes_activated.emit(problem_node_ids(*entry))
