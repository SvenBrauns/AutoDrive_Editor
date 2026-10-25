from dataclasses import dataclass

from PySide6.QtCore import (
    QSize,
    Qt
)
from PySide6.QtGui import (
    QAction,
    QActionGroup,
    QIcon,
    QKeySequence
)
from PySide6.QtWidgets import (
    QMainWindow,
    QSizePolicy,
    QToolBar,
    QToolButton,
    QWidget
)

from app_paths import TOOL_ICON_DIRECTORY

from ui.interaction_mode import InteractionMode
from ui.rotation_controls import RotationControls
from ui.grid_controls import GridControls
from ui.tool_panel import ToolPanel
from measurement.measurement_mode import (
    MeasurementMode
)


@dataclass(frozen=True)
class ToolDefinition:

    interaction_mode: InteractionMode
    text: str
    description: str
    icon: str
    shortcut: str


def tool_icon(name: str) -> QIcon:
    return QIcon(
        str(TOOL_ICON_DIRECTORY / f"{name}.svg")
    )


def tool_tooltip(
    text: str,
    shortcut: str,
    description: str
) -> str:
    return (
        f"<b>{text}</b> ({shortcut})<br>{description}"
    )


NAVIGATION_TOOL = ToolDefinition(
    InteractionMode.NAVIGATE,
    "Navigation",
    "Kartenansicht verschieben und drehen",
    "navigate",
    "N"
)

SELECTION_TOOL = ToolDefinition(
    InteractionMode.SELECT,
    "Auswahl",
    "Nodes per Klick oder Rechtsziehen auswählen",
    "select",
    "A"
)

MOVE_TOOL = ToolDefinition(
    InteractionMode.MOVE_NODES,
    "Verschieben",
    "Node oder Auswahl per Linkes Ziehen verschieben",
    "move",
    "V"
)

CREATE_REGULAR_TOOL = ToolDefinition(
    InteractionMode.CREATE_NODES,
    "Erstellen (Regular)",
    "Per Linksklick auf freie Fläche eine Regular-Node erstellen",
    "create_regular",
    "E"
)

CREATE_SUBPRIO_TOOL = ToolDefinition(
    InteractionMode.CREATE_SUBPRIO_NODES,
    "Erstellen (Subprio)",
    "Per Linksklick auf freie Fläche eine Subprio-Node erstellen",
    "create_subprio",
    "Shift+E"
)

TOGGLE_TYPE_TOOL = ToolDefinition(
    InteractionMode.TOGGLE_NODE_TYPE,
    "Typ wechseln",
    "Node oder Auswahl per Linksklick zwischen Regular und "
    "Subprio umschalten",
    "toggle_type",
    "T"
)

ROTATE_TOOL = ToolDefinition(
    InteractionMode.ROTATE_SELECTION,
    "Rotieren",
    "Auswahl am Ring um ihren Mittelpunkt drehen "
    "(Umschalt: 15°-Schritte)",
    "rotate",
    "R"
)

DELETE_TOOL = ToolDefinition(
    InteractionMode.DELETE_NODES,
    "Löschen",
    "Node oder Auswahl per Linksklick löschen",
    "delete",
    "L"
)

CONNECT_REGULAR_TOOL = ToolDefinition(
    InteractionMode.CONNECT_REGULAR,
    "Verbinden (Regular)",
    "Nodes nacheinander anklicken, um sie mit "
    "Regular-Connections zu verbinden",
    "connect_regular",
    "1"
)

CONNECT_DUAL_TOOL = ToolDefinition(
    InteractionMode.CONNECT_DUAL,
    "Verbinden (Dual)",
    "Nodes nacheinander anklicken, um sie mit "
    "Dual-Connections zu verbinden",
    "connect_dual",
    "2"
)

CONNECT_REVERSE_TOOL = ToolDefinition(
    InteractionMode.CONNECT_REVERSE,
    "Verbinden (Reverse)",
    "Nodes nacheinander anklicken, um sie mit "
    "Reverse-Connections zu verbinden",
    "connect_reverse",
    "3"
)


class MainWindowActions:

    # Tool groups in the left tool panel. Each row holds two tools:
    # node actions on the left, connection actions on the right.
    # None leaves a cell empty.
    TOOL_GROUPS = (
        (
            "Nodes",
            (
                (MOVE_TOOL, CONNECT_REGULAR_TOOL),
                (CREATE_REGULAR_TOOL, CONNECT_DUAL_TOOL),
                (CREATE_SUBPRIO_TOOL, CONNECT_REVERSE_TOOL),
                (TOGGLE_TYPE_TOOL, None),
                (ROTATE_TOOL, DELETE_TOOL),
            )
        ),
    )

    MAP_SCALES = (
        ("Originalgröße", 1),
        ("4x-Karte", 2),
        ("16x-Karte", 4),
        ("64x-Karte", 8)
    )

    def __init__(
        self,
        window: QMainWindow
    ):
        self.window = window

        self.map_scale_actions = {}

        self._create_actions()
        self._create_tool_panel()
        self._create_menu_bar()
        self._create_quick_access_toolbar()

    def _create_actions(self):
        # One exclusive group for all map tools, so exactly one tool
        # is active. The measuring tools un-check it while measuring.
        self.tool_actions: dict[InteractionMode, QAction] = {}

        self.navigation_action = self._create_tool_action(
            NAVIGATION_TOOL
        )

        self.selection_action = self._create_tool_action(
            SELECTION_TOOL
        )

        for _, rows in self.TOOL_GROUPS:
            for row in rows:
                for definition in row:
                    if definition is not None:
                        self._create_tool_action(
                            definition
                        )

        self.interaction_action_group = QActionGroup(
            self.window
        )

        self.interaction_action_group.setExclusive(
            True
        )

        for interaction_mode, action in self.tool_actions.items():
            self.interaction_action_group.addAction(
                action
            )

            action.triggered.connect(
                lambda checked, mode=interaction_mode:
                self._activate_tool(mode, checked)
            )

        self.navigation_action.setChecked(
            True
        )

        self.distance_measurement_action = QAction(
            "↔",
            self.window
        )

        self.distance_measurement_action.setCheckable(
            True
        )

        self.distance_measurement_action.setToolTip(
            "Abstand zwischen zwei Punkten messen"
        )

        self.distance_measurement_action.setStatusTip(
            "Abstand zwischen Nodes oder freien "
            "Kartenpunkten messen"
        )

        self.distance_measurement_action.triggered.connect(
            self._toggle_distance_measurement
        )

        self.angle_measurement_action = QAction(
            "∠",
            self.window
        )

        self.angle_measurement_action.setCheckable(
            True
        )

        self.angle_measurement_action.setToolTip(
            "Kartenwinkel zwischen zwei Punkten messen"
        )

        self.angle_measurement_action.setStatusTip(
            "Richtungswinkel zwischen Nodes oder freien "
            "Kartenpunkten messen"
        )

        self.angle_measurement_action.triggered.connect(
            self._toggle_angle_measurement
        )

        self.align_measurement_action = QAction(
            "━",
            self.window
        )

        self.align_measurement_action.setToolTip(
            "Messlinie horizontal ausrichten"
        )

        self.align_measurement_action.setStatusTip(
            "Ansicht so drehen, dass Messpunkt A "
            "links und Messpunkt B rechts liegt"
        )

        self.align_measurement_action.setEnabled(
            False
        )

        self.align_measurement_action.triggered.connect(
            self.window.align_view_to_measurement
        )

        self.load_project_action = QAction(
            "Projekt laden",
            self.window
        )

        self.load_project_action.triggered.connect(
            self.window.load_project
        )

        self.save_project_action = QAction(
            "Projekt speichern",
            self.window
        )

        self.save_project_action.triggered.connect(
            self.window.save_project
        )

        self.load_xml_action = QAction(
            "AutoDrive-XML laden",
            self.window
        )

        self.load_xml_action.triggered.connect(
            self.window.load_xml
        )

        self.exit_action = QAction(
            "Beenden",
            self.window
        )

        self.exit_action.triggered.connect(
            self.window.close
        )

        self.display_options_action = QAction(
            "Darstellungsoptionen...",
            self.window
        )

        self.display_options_action.triggered.connect(
            self.window.open_display_options
        )

        self.reset_view_action = QAction(
            "Ansicht zurücksetzen",
            self.window
        )

        self.reset_view_action.setEnabled(
            False
        )

        self.reset_rotation_action = QAction(
            "Rotation zurücksetzen",
            self.window
        )

        self.reset_rotation_action.setEnabled(
            False
        )

        self.reset_rotation_action.triggered.connect(
            self.window.reset_view_rotation
        )

        self.select_background_action = QAction(
            "DDS auswählen",
            self.window
        )

        self.select_background_action.triggered.connect(
            self.window.select_background
        )

        self.select_heightmap_action = QAction(
            "Heightmap auswählen",
            self.window
        )

        self.select_heightmap_action.triggered.connect(
            self.window.select_heightmap
        )

        self.remove_heightmap_action = QAction(
            "Heightmap entfernen",
            self.window
        )

        self.remove_heightmap_action.triggered.connect(
            self.window.remove_heightmap
        )

        self.remove_heightmap_action.setEnabled(
            False
        )

        self._create_undo_actions()
        self._create_delete_selection_action()

        self._create_map_scale_actions()

    def _create_map_scale_actions(self):
        self.map_scale_action_group = QActionGroup(
            self.window
        )

        self.map_scale_action_group.setExclusive(
            True
        )

        for label, map_scale in self.MAP_SCALES:
            action = QAction(
                label,
                self.window
            )

            action.setCheckable(
                True
            )

            action.setData(
                map_scale
            )

            action.triggered.connect(
                lambda checked, selected_scale=map_scale:
                self.window.set_map_scale(
                    selected_scale
                )
                if checked
                else None
            )

            self.map_scale_action_group.addAction(
                action
            )

            self.map_scale_actions[
                map_scale
            ] = action

    UNDO_TEXT = "Rückgängig"
    REDO_TEXT = "Wiederholen"

    def _create_tool_action(
        self,
        definition: ToolDefinition
    ) -> QAction:
        action = QAction(
            tool_icon(definition.icon),
            definition.text,
            self.window
        )

        action.setCheckable(
            True
        )

        action.setShortcut(
            QKeySequence(definition.shortcut)
        )

        action.setToolTip(
            tool_tooltip(
                definition.text,
                definition.shortcut,
                definition.description
            )
        )

        action.setStatusTip(
            definition.description
        )

        # Added to the window so the shortcut also works while the
        # tool panel is hidden.
        self.window.addAction(
            action
        )

        self.tool_actions[
            definition.interaction_mode
        ] = action

        return action

    def _create_undo_actions(self):
        edit_coordinator = self.window.edit_coordinator
        undo_stack = edit_coordinator.undo_stack

        self.undo_action = self._create_history_action(
            icon="undo",
            base_text=self.UNDO_TEXT,
            shortcut=QKeySequence.Undo,
            trigger=edit_coordinator.undo,
            can_run_changed=undo_stack.canUndoChanged,
            text_changed=undo_stack.undoTextChanged
        )

        self.redo_action = self._create_history_action(
            icon="redo",
            base_text=self.REDO_TEXT,
            shortcut=QKeySequence.Redo,
            trigger=edit_coordinator.redo,
            can_run_changed=undo_stack.canRedoChanged,
            text_changed=undo_stack.redoTextChanged
        )

    def _create_delete_selection_action(self):
        self.delete_selection_action = QAction(
            "Auswahl löschen",
            self.window
        )

        self.delete_selection_action.setShortcut(
            QKeySequence.Delete
        )

        self.delete_selection_action.setEnabled(
            False
        )

        self.delete_selection_action.triggered.connect(
            self.window.delete_selection
        )

    def _create_history_action(
        self,
        icon: str,
        base_text: str,
        shortcut,
        trigger,
        can_run_changed,
        text_changed
    ) -> QAction:
        action = QAction(
            tool_icon(icon),
            base_text,
            self.window
        )

        action.setShortcuts(
            shortcut
        )

        action.setEnabled(
            False
        )

        action.triggered.connect(
            trigger
        )

        can_run_changed.connect(
            action.setEnabled
        )

        # Shows e.g. "Rückgängig: Node verschieben".
        text_changed.connect(
            lambda command_text: action.setText(
                f"{base_text}: {command_text}"
                if command_text
                else base_text
            )
        )

        return action

    def _create_menu_bar(self):
        menu_bar = self.window.menuBar()

        file_menu = menu_bar.addMenu(
            "Datei"
        )

        file_menu.addAction(
            self.load_project_action
        )

        file_menu.addAction(
            self.save_project_action
        )

        file_menu.addSeparator()

        file_menu.addAction(
            self.load_xml_action
        )

        file_menu.addSeparator()

        file_menu.addAction(
            self.exit_action
        )

        edit_menu = menu_bar.addMenu(
            "Bearbeiten"
        )

        edit_menu.addAction(
            self.undo_action
        )

        edit_menu.addAction(
            self.redo_action
        )

        edit_menu.addSeparator()

        edit_menu.addAction(
            self.delete_selection_action
        )

        view_menu = menu_bar.addMenu(
            "Ansicht"
        )

        view_menu.addAction(
            self.display_options_action
        )

        view_menu.addSeparator()

        view_menu.addAction(
            self.tool_panel.toggleViewAction()
        )

        view_menu.addAction(
            self.tool_labels_action
        )

        view_menu.addAction(
            self.window.debug_dock.toggleViewAction()
        )

        view_menu.addSeparator()

        view_menu.addAction(
            self.reset_view_action
        )

        view_menu.addAction(
            self.reset_rotation_action
        )

        map_menu = menu_bar.addMenu(
            "Karte"
        )

        map_menu.addAction(
            self.select_background_action
        )

        map_menu.addSeparator()

        map_menu.addAction(
            self.select_heightmap_action
        )

        map_menu.addAction(
            self.remove_heightmap_action
        )

        map_menu.addSeparator()

        map_size_menu = map_menu.addMenu(
            "Kartengröße"
        )

        for _, map_scale in self.MAP_SCALES:
            map_size_menu.addAction(
                self.map_scale_actions[
                    map_scale
                ]
            )

    def _create_quick_access_toolbar(self):
        self.quick_access_toolbar = QToolBar(
            "Schnellauswahl",
            self.window
        )

        self.quick_access_toolbar.setObjectName(
            "quick_access_toolbar"
        )

        self.quick_access_toolbar.setMovable(
            False
        )

        self.quick_access_toolbar.setFloatable(
            False
        )

        self.quick_access_toolbar.setToolButtonStyle(
            Qt.ToolButtonTextOnly
        )

        self.window.addToolBar(
            Qt.TopToolBarArea,
            self.quick_access_toolbar
        )

        # Icon only: the action text grows to e.g. "Rückgängig: 3 Nodes
        # verschieben", which is shown as tooltip instead.
        for action in (
            self.undo_action,
            self.redo_action
        ):
            button = QToolButton(
                self.quick_access_toolbar
            )

            button.setDefaultAction(
                action
            )

            button.setToolButtonStyle(
                Qt.ToolButtonIconOnly
            )

            button.setIconSize(
                QSize(20, 20)
            )

            button.setAutoRaise(
                True
            )

            self.quick_access_toolbar.addWidget(
                button
            )

        self.quick_access_toolbar.addSeparator()

        self.quick_access_toolbar.addAction(
            self.navigation_action
        )

        self.quick_access_toolbar.addAction(
            self.selection_action
        )

        spacer = QWidget(
            self.quick_access_toolbar
        )

        spacer.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Preferred
        )

        self.quick_access_toolbar.addWidget(
            spacer
        )

        self.rotation_controls = RotationControls(
            rotation_angle=(
                self.window.view.rotation_angle
            ),
            rotation_step=(
                self.window.view.rotation_step
            ),
            parent=self.quick_access_toolbar
        )

        self.rotation_controls.rotation_angle_requested.connect(
            self.window.set_view_rotation
        )

        self.rotation_controls.rotation_step_requested.connect(
            self.window.set_view_rotation_step
        )

        self.rotation_controls.reset_requested.connect(
            self.window.reset_view_rotation
        )

        self.quick_access_toolbar.addWidget(
            self.rotation_controls
        )

        self.grid_controls = GridControls(
            grid_visible=(
                self.window.background_manager.grid_visible
            ),
            grid_spacing=(
                self.window.background_manager.grid_spacing
            ),
            grid_rotation=(
                self.window.background_manager.grid_rotation
            ),
            parent=self.quick_access_toolbar
        )

        self.quick_access_toolbar.addWidget(
            self.grid_controls
        )

        self.quick_access_toolbar.addSeparator()

        self.quick_access_toolbar.addAction(
            self.distance_measurement_action
        )

        self.quick_access_toolbar.addAction(
            self.angle_measurement_action
        )

        self.quick_access_toolbar.addAction(
            self.align_measurement_action
        )

    def _create_tool_panel(self):
        self.tool_panel = ToolPanel(
            self.window
        )

        for group_title, rows in self.TOOL_GROUPS:
            self.tool_panel.add_tool_group(
                group_title,
                [
                    tuple(
                        self.tool_actions[definition.interaction_mode]
                        if definition is not None
                        else None
                        for definition in row
                    )
                    for row in rows
                ]
            )

        self.tool_labels_action = QAction(
            "Werkzeugbeschriftungen anzeigen",
            self.window
        )

        self.tool_labels_action.setCheckable(
            True
        )

        self.tool_labels_action.toggled.connect(
            self.tool_panel.set_labels_visible
        )

        self.window.addDockWidget(
            Qt.LeftDockWidgetArea,
            self.tool_panel
        )

    def set_current_map_scale(
        self,
        map_scale: int
    ):
        action = self.map_scale_actions.get(
            map_scale
        )

        if action is not None:
            action.setChecked(
                True
            )

    def set_measurement_mode(
        self,
        measurement_mode: MeasurementMode
    ):
        if not isinstance(
            measurement_mode,
            MeasurementMode
        ):
            raise TypeError(
                "Der Messmodus ist ungültig."
            )

        distance_active = (
            measurement_mode
            == MeasurementMode.DISTANCE
        )

        angle_active = (
            measurement_mode
            == MeasurementMode.ANGLE
        )

        measurement_active = (
            distance_active
            or angle_active
        )

        self.distance_measurement_action.blockSignals(
            True
        )

        self.distance_measurement_action.setChecked(
            distance_active
        )

        self.distance_measurement_action.blockSignals(
            False
        )

        self.angle_measurement_action.blockSignals(
            True
        )

        self.angle_measurement_action.setChecked(
            angle_active
        )

        self.angle_measurement_action.blockSignals(
            False
        )

        if measurement_active:
            self._check_tool_action(
                None
            )

        else:
            self._restore_interaction_action()

    def _check_tool_action(
        self,
        interaction_mode: InteractionMode | None
    ):
        """Checks the action of the given tool, or none for None,
        without triggering it."""

        self.interaction_action_group.setExclusive(
            False
        )

        for mode, action in self.tool_actions.items():
            action.blockSignals(
                True
            )

            action.setChecked(
                mode == interaction_mode
            )

            action.blockSignals(
                False
            )

        self.interaction_action_group.setExclusive(
            True
        )

    def _restore_interaction_action(self):
        self._check_tool_action(
            self.window.view.interaction_mode
        )

    def sync_tool_actions(self):
        """Checks the button of the active tool, or none while
        measuring."""

        if self.window.view.measurement_active:
            self._check_tool_action(
                None
            )

        else:
            self._restore_interaction_action()

    def set_measurement_alignment_enabled(
        self,
        enabled: bool
    ):
        self.align_measurement_action.setEnabled(
            bool(enabled)
        )

    def _activate_tool(
        self,
        interaction_mode: InteractionMode,
        checked: bool
    ):
        if not checked:
            return

        was_measuring = (
            self.window.view.measurement_active
        )

        self.window.set_interaction_mode(
            interaction_mode
        )

        # Only end measuring if it was on, so the status bar keeps
        # showing the newly selected tool otherwise.
        if was_measuring:
            self.window.set_measurement_mode(
                MeasurementMode.INACTIVE
            )

    def _toggle_distance_measurement(
        self,
        checked: bool
    ):
        if checked:
            self.angle_measurement_action.setChecked(
                False
            )

            self.window.set_measurement_mode(
                MeasurementMode.DISTANCE
            )

            return

        if (
            self.window.measurement_controller.mode
            == MeasurementMode.DISTANCE
        ):
            self.window.set_measurement_mode(
                MeasurementMode.INACTIVE
            )

    def _toggle_angle_measurement(
        self,
        checked: bool
    ):
        if checked:
            self.distance_measurement_action.setChecked(
                False
            )

            self.window.set_measurement_mode(
                MeasurementMode.ANGLE
            )

            return

        if (
            self.window.measurement_controller.mode
            == MeasurementMode.ANGLE
        ):
            self.window.set_measurement_mode(
                MeasurementMode.INACTIVE
            )