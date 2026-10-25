from PySide6.QtCore import Qt
from PySide6.QtGui import (
    QAction,
    QActionGroup,
    QKeySequence
)
from PySide6.QtWidgets import (
    QMainWindow,
    QSizePolicy,
    QToolBar,
    QWidget
)

from ui.interaction_mode import InteractionMode
from ui.rotation_controls import RotationControls
from ui.grid_controls import GridControls
from measurement.measurement_mode import (
    MeasurementMode
)


class MainWindowActions:

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
        self._create_menu_bar()
        self._create_quick_access_toolbar()
        self._create_editor_toolbar()

    def _create_actions(self):
        self.navigation_action = QAction(
            "Navigation",
            self.window
        )

        self.navigation_action.setCheckable(
            True
        )

        self.navigation_action.setToolTip(
            "Kartenansicht verschieben und drehen"
        )

        self.navigation_action.triggered.connect(
            self._activate_navigation_mode
        )

        self.selection_action = QAction(
            "Auswahl",
            self.window
        )

        self.selection_action.setCheckable(
            True
        )

        self.selection_action.setToolTip(
            "Nodes und Connections auswählen"
        )

        self.selection_action.triggered.connect(
            self._activate_selection_mode
        )

        self.interaction_action_group = QActionGroup(
            self.window
        )

        self.interaction_action_group.setExclusive(
            True
        )

        self.interaction_action_group.addAction(
            self.navigation_action
        )

        self.interaction_action_group.addAction(
            self.selection_action
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

    def _create_undo_actions(self):
        undo_stack = (
            self.window.edit_coordinator.undo_stack
        )

        self.undo_action = self._create_history_action(
            base_text=self.UNDO_TEXT,
            shortcut=QKeySequence.Undo,
            trigger=undo_stack.undo,
            can_run_changed=undo_stack.canUndoChanged,
            text_changed=undo_stack.undoTextChanged
        )

        self.redo_action = self._create_history_action(
            base_text=self.REDO_TEXT,
            shortcut=QKeySequence.Redo,
            trigger=undo_stack.redo,
            can_run_changed=undo_stack.canRedoChanged,
            text_changed=undo_stack.redoTextChanged
        )

    def _create_history_action(
        self,
        base_text: str,
        shortcut,
        trigger,
        can_run_changed,
        text_changed
    ) -> QAction:
        action = QAction(
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

        view_menu = menu_bar.addMenu(
            "Ansicht"
        )

        view_menu.addAction(
            self.display_options_action
        )

        view_menu.addSeparator()

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

    def _create_editor_toolbar(self):
        self.editor_toolbar = QToolBar(
            "Editor-Werkzeuge",
            self.window
        )

        self.editor_toolbar.setObjectName(
            "editor_toolbar"
        )

        self.editor_toolbar.setMovable(
            False
        )

        self.editor_toolbar.setFloatable(
            False
        )

        self.editor_toolbar.setToolButtonStyle(
            Qt.ToolButtonTextUnderIcon
        )

        self.window.addToolBar(
            Qt.LeftToolBarArea,
            self.editor_toolbar
        )

        self.editor_placeholder_action = QAction(
            "Editor",
            self.window
        )

        self.editor_placeholder_action.setEnabled(
            False
        )

        self.editor_placeholder_action.setToolTip(
            "Editor-Werkzeuge werden später ergänzt"
        )

        self.editor_toolbar.addAction(
            self.editor_placeholder_action
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
            self._set_interaction_actions_checked(
                navigation_checked=False,
                selection_checked=False
            )

        else:
            self._restore_interaction_action()

    def _set_interaction_actions_checked(
        self,
        navigation_checked: bool,
        selection_checked: bool
    ):
        self.interaction_action_group.setExclusive(
            False
        )

        self.navigation_action.blockSignals(
            True
        )

        self.selection_action.blockSignals(
            True
        )

        self.navigation_action.setChecked(
            navigation_checked
        )

        self.selection_action.setChecked(
            selection_checked
        )

        self.navigation_action.blockSignals(
            False
        )

        self.selection_action.blockSignals(
            False
        )

        self.interaction_action_group.setExclusive(
            True
        )

    def _restore_interaction_action(self):
        interaction_mode = (
            self.window.view.interaction_mode
        )

        self._set_interaction_actions_checked(
            navigation_checked=(
                interaction_mode
                == InteractionMode.NAVIGATE
            ),
            selection_checked=(
                interaction_mode
                == InteractionMode.SELECT
            )
        )

    def set_measurement_alignment_enabled(
        self,
        enabled: bool
    ):
        self.align_measurement_action.setEnabled(
            bool(enabled)
        )

    def _activate_navigation_mode(
        self,
        checked: bool
    ):
        if not checked:
            return

        self.window.set_interaction_mode(
            InteractionMode.NAVIGATE
        )

        self.window.set_measurement_mode(
            MeasurementMode.INACTIVE
        )

    def _activate_selection_mode(
        self,
        checked: bool
    ):
        if not checked:
            return

        self.window.set_interaction_mode(
            InteractionMode.SELECT
        )

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