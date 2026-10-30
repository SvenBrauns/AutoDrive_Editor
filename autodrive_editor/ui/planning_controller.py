from collections.abc import Callable

from PySide6.QtCore import QObject
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QMessageBox, QPushButton, QWidget

from autodrive_editor.editing.commands.edit_command import DataChange
from autodrive_editor.editing.edit_history import EditHistory
from autodrive_editor.editing.plan_changes import PlanChanges
from autodrive_editor.i18n import tr
from autodrive_editor.model.autodrive_data import AutoDriveData
from autodrive_editor.rendering.scene_renderer import SceneRenderer
from autodrive_editor.ui.actions.tool_catalog import tool_icon
from autodrive_editor.ui.dialogs.messages import APP_TITLE

BAR_STYLE = (
    "#planning_bar { background: #1e90ff; }"
    "#planning_bar QLabel { color: white; font-weight: bold; }"
)


class PlanningController(QObject):
    """Planning mode: edits go into a plan that is applied as one undo step or discarded.
    Shows a bar above the map while planning and highlights the nodes the plan changed."""

    def __init__(
        self,
        window: QWidget,
        edit_history: EditHistory,
        scene_renderer: SceneRenderer,
        autodrive_data_provider: Callable[[], AutoDriveData | None],
    ):
        super().__init__(window)

        self.window = window
        self.edit_history = edit_history
        self.scene_renderer = scene_renderer
        self.autodrive_data_provider = autodrive_data_provider
        self.changes: PlanChanges | None = None

        self.action = QAction(tool_icon("planning"), tr("Planning mode"), window)
        self.action.setCheckable(True)
        self.action.setShortcut(QKeySequence("Ctrl+P"))
        self.action.setStatusTip(
            tr("Edit the network as a plan, then apply it as one undo step or discard it")
        )
        # Enabled once AutoDrive data is loaded.
        self.action.setEnabled(False)
        self.action.triggered.connect(self.toggle)

        self._create_bar()

        edit_history.planning_changed.connect(self._handle_planning_changed)
        edit_history.data_changed.connect(self._handle_data_changed)

    def _create_bar(self):
        self.bar = QFrame()
        self.bar.setObjectName("planning_bar")
        self.bar.setStyleSheet(BAR_STYLE)

        self.bar_label = QLabel(self.bar)
        self.apply_button = QPushButton(tr("Apply plan"), self.bar)
        self.apply_button.clicked.connect(self.edit_history.apply_plan)
        self.discard_button = QPushButton(tr("Discard plan"), self.bar)
        self.discard_button.clicked.connect(self.edit_history.discard_plan)

        layout = QHBoxLayout(self.bar)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.addWidget(self.bar_label, 1)
        layout.addWidget(self.apply_button)
        layout.addWidget(self.discard_button)

        self.bar.hide()

    def toggle(self):
        if self.edit_history.is_planning:
            self.confirm_end_plan()
        else:
            self.start_plan()

        # The click may have been cancelled.
        self.action.setChecked(self.edit_history.is_planning)

    def start_plan(self):
        autodrive_data = self.autodrive_data_provider()

        if autodrive_data is None or self.edit_history.is_planning:
            return

        self.changes = PlanChanges(autodrive_data)
        self.edit_history.start_plan()

    def confirm_end_plan(self) -> bool:
        """Asks whether to apply or discard an open plan. Returns whether to go on."""

        if not self.edit_history.is_planning:
            return True

        if not self.edit_history.has_plan_edits:
            self.edit_history.discard_plan()
            return True

        answer = self._ask_end_plan()

        if answer == QMessageBox.Apply:
            self.edit_history.apply_plan()
        elif answer == QMessageBox.Discard:
            self.edit_history.discard_plan()
        else:
            return False

        return True

    def _ask_end_plan(self):
        box = QMessageBox(
            QMessageBox.Question,
            APP_TITLE,
            tr("The plan is not applied yet. Apply it?"),
            QMessageBox.Apply | QMessageBox.Discard | QMessageBox.Cancel,
            self.window,
        )
        # Same words as on the planning bar.
        box.button(QMessageBox.Apply).setText(tr("Apply plan"))
        box.button(QMessageBox.Discard).setText(tr("Discard plan"))
        box.setDefaultButton(QMessageBox.Apply)

        return box.exec()

    def _handle_planning_changed(self, planning: bool):
        self.action.setChecked(planning)
        self.bar.setVisible(planning)

        if not planning:
            self.changes = None
            self.scene_renderer.set_plan_node_ids(())

        self._update_bar()

    def _handle_data_changed(self, data_change: DataChange):
        if self.changes is None:
            return

        self.changes.update(data_change)
        self.scene_renderer.set_plan_node_ids(self.changes.changed_node_ids)
        self._update_bar()

    def _update_bar(self):
        count = len(self.changes.changed_node_ids) if self.changes is not None else 0

        self.bar_label.setText(tr("Planning – {count} nodes changed", count=count))
