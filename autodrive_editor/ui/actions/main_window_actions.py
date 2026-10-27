from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QAction, QActionGroup, QKeySequence
from PySide6.QtWidgets import QMainWindow, QSizePolicy, QToolBar, QToolButton, QWidget

from autodrive_editor.i18n import tr
from autodrive_editor.measurement.mode import MeasurementMode
from autodrive_editor.ui.actions.tool_catalog import (
    NAVIGATION_TOOL,
    SELECTION_TOOL,
    TOOL_GROUPS,
    ToolDefinition,
    history_icon,
    tool_icon,
    tool_tooltip,
)
from autodrive_editor.ui.controls.grid_controls import GridControls
from autodrive_editor.ui.controls.rotation_controls import RotationControls
from autodrive_editor.ui.panels.tool_panel import ToolPanel
from autodrive_editor.ui.tools.interaction_mode import InteractionMode

TOOLBAR_ICON_SIZE = QSize(28, 28)
TOOLBAR_GAP_WIDTH = 8


class MainWindowActions:
    """Creates the window's actions, menus, toolbars and tool panel, and keeps the tool buttons in
    sync with the active tool.
    """

    MAP_SCALES = (
        (tr("Original size"), 1),
        (tr("4x map"), 2),
        (tr("16x map"), 4),
        (tr("64x map"), 8),
    )

    def __init__(self, window: QMainWindow):
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

        self.navigation_action = self._create_tool_action(NAVIGATION_TOOL)

        self.selection_action = self._create_tool_action(SELECTION_TOOL)

        for _, rows in TOOL_GROUPS:
            for row in rows:
                for definition in row:
                    if definition is not None:
                        self._create_tool_action(definition)

        self.interaction_action_group = QActionGroup(self.window)

        self.interaction_action_group.setExclusive(True)

        for interaction_mode, action in self.tool_actions.items():
            self.interaction_action_group.addAction(action)

            action.triggered.connect(
                lambda checked, mode=interaction_mode: self._activate_tool(mode, checked)
            )

        self.navigation_action.setChecked(True)

        self.distance_measurement_action = QAction(tool_icon("measure_distance"), "↔", self.window)

        self.distance_measurement_action.setCheckable(True)

        self.distance_measurement_action.setToolTip(tr("Measure the distance between two points"))

        self.distance_measurement_action.setStatusTip(
            tr("Measure the distance between nodes or free map points")
        )

        self.distance_measurement_action.triggered.connect(self._toggle_distance_measurement)

        self.angle_measurement_action = QAction(tool_icon("measure_angle"), "∠", self.window)

        self.angle_measurement_action.setCheckable(True)

        self.angle_measurement_action.setToolTip(tr("Measure the map angle between two points"))

        self.angle_measurement_action.setStatusTip(
            tr("Measure the direction angle between nodes or free map points")
        )

        self.angle_measurement_action.triggered.connect(self._toggle_angle_measurement)

        self.align_measurement_action = QAction(tool_icon("measure_align"), "━", self.window)

        self.align_measurement_action.setToolTip(tr("Align the measuring line horizontally"))

        self.align_measurement_action.setStatusTip(
            tr("Rotate the view so that point A is on the left and point B on the right")
        )

        self.align_measurement_action.setEnabled(False)

        self.align_measurement_action.triggered.connect(self.window.align_view_to_measurement)

        self.load_project_action = QAction(tr("Load project"), self.window)

        self.load_project_action.triggered.connect(self.window.files.load_project)

        self.save_project_action = QAction(tr("Save project"), self.window)

        self.save_project_action.triggered.connect(self.window.files.save_project)

        self.open_route_action = QAction(tr("Open route…"), self.window)
        self.open_route_action.setStatusTip(
            tr("Open a route from the RoutesManager of the game folder")
        )
        self.open_route_action.triggered.connect(self.window.files.open_route)

        self.open_savegame_action = QAction(tr("Open savegame…"), self.window)
        self.open_savegame_action.setStatusTip(tr("Open the AutoDrive data of a savegame"))
        self.open_savegame_action.triggered.connect(self.window.files.open_savegame)

        self.load_xml_action = QAction(tr("Open XML file…"), self.window)

        self.load_xml_action.triggered.connect(self.window.files.load_xml)

        self.save_xml_action = QAction(tr("Save"), self.window)
        self.save_xml_action.setShortcut(QKeySequence.Save)
        self.save_xml_action.setStatusTip(tr("Save the AutoDrive data into the loaded file"))
        self.save_xml_action.setEnabled(False)
        self.save_xml_action.triggered.connect(self.window.files.save_xml)

        self.save_xml_as_action = QAction(tr("Save as…"), self.window)
        self.save_xml_as_action.setShortcut(QKeySequence.SaveAs)
        self.save_xml_as_action.setStatusTip(
            tr("Save routes as a new route in the RoutesManager, anything else into another file")
        )
        self.save_xml_as_action.setEnabled(False)
        self.save_xml_as_action.triggered.connect(self.window.files.save_xml_as)

        self.settings_action = QAction(tr("Settings…"), self.window)

        self.settings_action.triggered.connect(self.window.open_settings)

        self.exit_action = QAction(tr("Exit"), self.window)

        self.exit_action.triggered.connect(self.window.close)

        self.display_options_action = QAction(tr("Display options…"), self.window)

        self.display_options_action.triggered.connect(self.window.open_display_options)

        self.reset_view_action = QAction(tr("Reset view"), self.window)

        self.reset_view_action.setEnabled(False)

        self.reset_rotation_action = QAction(tr("Reset rotation"), self.window)

        self.reset_rotation_action.setEnabled(False)

        self.reset_rotation_action.triggered.connect(self.window.reset_view_rotation)

        self.import_map_mod_action = QAction(tr("Import map from mod…"), self.window)
        self.import_map_mod_action.setStatusTip(
            tr("Import the map image and heightmap from a map mod (zip)")
        )
        self.import_map_mod_action.triggered.connect(self.window.map_import.import_map_mod)

        self.scan_map_mods_action = QAction(tr("Scan maps…"), self.window)
        self.scan_map_mods_action.setStatusTip(
            tr("Search the mods folder for map mods and import maps")
        )
        self.scan_map_mods_action.triggered.connect(self.window.map_import.scan_map_mods)

        self.select_background_action = QAction(tr("Choose DDS"), self.window)

        self.select_background_action.triggered.connect(self.window.files.select_background)

        self.select_heightmap_action = QAction(tr("Choose heightmap"), self.window)

        self.select_heightmap_action.triggered.connect(self.window.files.select_heightmap)

        self.remove_heightmap_action = QAction(tr("Remove heightmap"), self.window)

        self.remove_heightmap_action.triggered.connect(
            self.window.project_coordinator.remove_heightmap
        )

        self.remove_heightmap_action.setEnabled(False)

        self.check_network_action = QAction(tr("Check network"), self.window)
        self.check_network_action.setStatusTip(
            tr("Find overlapping nodes, nodes outside the map and wrong heights")
        )
        self.check_network_action.triggered.connect(self.window.network_check.run)

        self._create_undo_actions()
        self._create_delete_selection_action()

        self._create_clipboard_actions()

        self.grid_snap_action = QAction(tool_icon("grid_snap"), tr("Snap to grid"), self.window)
        self.grid_snap_action.setCheckable(True)
        self.grid_snap_action.setShortcut(QKeySequence("G"))
        self.grid_snap_action.toggled.connect(
            lambda enabled: self.window.grid_coordinator.set_grid_snap_enabled(enabled)
        )

        self._create_map_scale_actions()

    def _create_map_scale_actions(self):
        self.map_scale_action_group = QActionGroup(self.window)

        self.map_scale_action_group.setExclusive(True)

        for label, map_scale in self.MAP_SCALES:
            action = QAction(label, self.window)

            action.setCheckable(True)

            action.setData(map_scale)

            action.triggered.connect(
                lambda checked, selected_scale=map_scale: (
                    self.window.set_map_scale(selected_scale) if checked else None
                )
            )

            self.map_scale_action_group.addAction(action)

            self.map_scale_actions[map_scale] = action

    UNDO_TEXT = tr("Undo")
    REDO_TEXT = tr("Redo")

    def _create_tool_action(self, definition: ToolDefinition) -> QAction:
        action = QAction(tool_icon(definition.icon), definition.text, self.window)

        action.setCheckable(True)

        action.setShortcut(QKeySequence(definition.shortcut))

        action.setToolTip(
            tool_tooltip(definition.text, definition.shortcut, definition.description)
        )

        action.setStatusTip(definition.description)

        # Added to the window so the shortcut also works while the
        # tool panel is hidden.
        self.window.addAction(action)

        self.tool_actions[definition.interaction_mode] = action

        return action

    def _create_undo_actions(self):
        edit_history = self.window.edit_history
        undo_stack = edit_history.undo_stack

        self.undo_action = self._create_history_action(
            icon="undo",
            base_text=self.UNDO_TEXT,
            shortcut=QKeySequence.Undo,
            trigger=edit_history.undo,
            can_run_changed=undo_stack.canUndoChanged,
            text_changed=undo_stack.undoTextChanged,
        )

        self.redo_action = self._create_history_action(
            icon="redo",
            base_text=self.REDO_TEXT,
            shortcut=QKeySequence.Redo,
            trigger=edit_history.redo,
            can_run_changed=undo_stack.canRedoChanged,
            text_changed=undo_stack.redoTextChanged,
        )

    def _create_delete_selection_action(self):
        self.delete_selection_action = QAction(tr("Delete selection"), self.window)

        self.delete_selection_action.setShortcut(QKeySequence.Delete)

        self.delete_selection_action.setEnabled(False)

        self.delete_selection_action.triggered.connect(self.window.delete_selection)

    def _create_clipboard_actions(self):
        clipboard = self.window.clipboard_operation

        definitions = (
            ("copy_action", "copy", tr("Copy"), QKeySequence.Copy, clipboard.copy),
            ("cut_action", "cut", tr("Cut"), QKeySequence.Cut, clipboard.cut),
            ("paste_action", "paste", tr("Paste"), QKeySequence.Paste, clipboard.paste),
            (
                "paste_at_original_action",
                "paste",
                tr("Paste at original position"),
                QKeySequence("Ctrl+Shift+V"),
                lambda: clipboard.paste(at_original_position=True),
            ),
        )

        for name, icon, text, shortcut, trigger in definitions:
            action = QAction(tool_icon(icon), text, self.window)
            action.setShortcut(shortcut)
            action.triggered.connect(trigger)
            setattr(self, name, action)

    def _create_history_action(
        self, icon: str, base_text: str, shortcut, trigger, can_run_changed, text_changed
    ) -> QAction:
        action = QAction(history_icon(icon), base_text, self.window)

        action.setShortcuts(shortcut)

        action.setEnabled(False)

        action.triggered.connect(trigger)

        can_run_changed.connect(action.setEnabled)

        # Shows e.g. "Undo: Move node".
        text_changed.connect(
            lambda command_text: action.setText(
                f"{base_text}: {command_text}" if command_text else base_text
            )
        )

        return action

    def _create_menu_bar(self):
        menu_bar = self.window.menuBar()

        file_menu = menu_bar.addMenu(tr("File"))

        file_menu.addAction(self.open_route_action)

        file_menu.addAction(self.open_savegame_action)

        file_menu.addAction(self.load_xml_action)

        file_menu.addAction(self.save_xml_action)

        file_menu.addAction(self.save_xml_as_action)

        file_menu.addSeparator()

        file_menu.addAction(self.load_project_action)

        file_menu.addAction(self.save_project_action)

        file_menu.addSeparator()

        file_menu.addAction(self.settings_action)

        file_menu.addSeparator()

        file_menu.addAction(self.exit_action)

        edit_menu = menu_bar.addMenu(tr("Edit"))

        edit_menu.addAction(self.undo_action)

        edit_menu.addAction(self.redo_action)

        edit_menu.addSeparator()

        edit_menu.addAction(self.copy_action)

        edit_menu.addAction(self.cut_action)

        edit_menu.addAction(self.paste_action)

        edit_menu.addAction(self.paste_at_original_action)

        edit_menu.addSeparator()

        edit_menu.addAction(self.delete_selection_action)

        edit_menu.addSeparator()

        edit_menu.addAction(self.grid_snap_action)

        view_menu = menu_bar.addMenu(tr("View"))

        view_menu.addAction(self.display_options_action)

        view_menu.addSeparator()

        view_menu.addAction(self.tool_panel.toggleViewAction())

        view_menu.addAction(self.tool_labels_action)

        view_menu.addAction(self.window.marker_dock.toggleViewAction())

        view_menu.addAction(self.window.check_dock.toggleViewAction())

        view_menu.addAction(self.window.debug_dock.toggleViewAction())

        view_menu.addSeparator()

        view_menu.addAction(self.marker_names_action)

        view_menu.addSeparator()

        view_menu.addAction(self.reset_view_action)

        view_menu.addAction(self.reset_rotation_action)

        map_menu = menu_bar.addMenu(tr("Map"))

        map_menu.addAction(self.scan_map_mods_action)

        map_menu.addAction(self.import_map_mod_action)

        map_menu.addSeparator()

        map_menu.addAction(self.select_background_action)

        map_menu.addSeparator()

        map_menu.addAction(self.select_heightmap_action)

        map_menu.addAction(self.remove_heightmap_action)

        map_menu.addSeparator()

        map_size_menu = map_menu.addMenu(tr("Map size"))

        for _, map_scale in self.MAP_SCALES:
            map_size_menu.addAction(self.map_scale_actions[map_scale])

        check_menu = menu_bar.addMenu(tr("Check"))

        check_menu.addAction(self.check_network_action)

    def _create_quick_access_toolbar(self):
        self.quick_access_toolbar = QToolBar(tr("Quick access"), self.window)

        self.quick_access_toolbar.setObjectName("quick_access_toolbar")

        self.quick_access_toolbar.setMovable(False)

        self.quick_access_toolbar.setFloatable(False)

        self.quick_access_toolbar.setToolButtonStyle(Qt.ToolButtonIconOnly)

        self.quick_access_toolbar.setIconSize(TOOLBAR_ICON_SIZE)

        self.window.addToolBar(Qt.TopToolBarArea, self.quick_access_toolbar)

        # Icon only: the action text grows to e.g. "Rückgängig: 3 Nodes
        # verschieben", which is shown as tooltip instead.
        for action in (self.undo_action, self.redo_action):
            button = QToolButton(self.quick_access_toolbar)

            button.setDefaultAction(action)

            button.setToolButtonStyle(Qt.ToolButtonIconOnly)

            button.setIconSize(TOOLBAR_ICON_SIZE)

            button.setAutoRaise(True)

            self.quick_access_toolbar.addWidget(button)

        self._add_toolbar_gap()

        self.quick_access_toolbar.addAction(self.navigation_action)

        self.quick_access_toolbar.addAction(self.selection_action)

        self._add_toolbar_gap()

        for action in (self.copy_action, self.cut_action, self.paste_action):
            self.quick_access_toolbar.addAction(action)

        spacer = QWidget(self.quick_access_toolbar)

        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        self.quick_access_toolbar.addWidget(spacer)

        self.rotation_controls = RotationControls(
            rotation_angle=self.window.view.rotation_angle,
            rotation_step=self.window.view.rotation_step,
            parent=self.quick_access_toolbar,
        )

        self.rotation_controls.rotation_angle_requested.connect(self.window.set_view_rotation)

        self.rotation_controls.rotation_step_requested.connect(self.window.set_view_rotation_step)

        self.rotation_controls.reset_requested.connect(self.window.reset_view_rotation)

        self._show_as_icon(self.rotation_controls, "view_rotation")

        self.quick_access_toolbar.addWidget(self.rotation_controls)

        self.grid_controls = GridControls(
            grid_visible=self.window.background_map.grid_visible,
            grid_spacing=self.window.background_map.grid_spacing,
            grid_rotation=self.window.background_map.grid_rotation,
            parent=self.quick_access_toolbar,
        )

        self._show_as_icon(self.grid_controls, "grid")

        self.quick_access_toolbar.addWidget(self.grid_controls)

        self.quick_access_toolbar.addAction(self.grid_snap_action)

        self.grid_controls.snap_requested.connect(self.grid_snap_action.setChecked)

        self.quick_access_toolbar.addSeparator()

        self.quick_access_toolbar.addAction(self.distance_measurement_action)

        self.quick_access_toolbar.addAction(self.angle_measurement_action)

        self.quick_access_toolbar.addAction(self.align_measurement_action)

    def _add_toolbar_gap(self):
        """Separator with some free space on both sides, between button groups."""
        toolbar = self.quick_access_toolbar

        for item in ("gap", "separator", "gap"):
            if item == "separator":
                toolbar.addSeparator()
            else:
                gap = QWidget(toolbar)
                gap.setFixedWidth(TOOLBAR_GAP_WIDTH)
                toolbar.addWidget(gap)

    @staticmethod
    def _show_as_icon(button: QToolButton, icon: str):
        button.setIcon(tool_icon(icon))

        button.setIconSize(TOOLBAR_ICON_SIZE)

        button.setToolButtonStyle(Qt.ToolButtonIconOnly)

        button.setAutoRaise(True)

    def _create_tool_panel(self):
        self.tool_panel = ToolPanel(self.window)

        for group_title, rows in TOOL_GROUPS:
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
                ],
            )

        self.tool_labels_action = QAction(tr("Show tool labels"), self.window)

        self.tool_labels_action.setCheckable(True)

        self.tool_labels_action.toggled.connect(self.tool_panel.set_labels_visible)

        self.marker_names_action = QAction(tr("Show marker names"), self.window)
        self.marker_names_action.setCheckable(True)
        self.marker_names_action.setChecked(self.window.settings.marker_names_visible)
        self.marker_names_action.toggled.connect(self.window.set_marker_names_visible)

        self.window.addDockWidget(Qt.LeftDockWidgetArea, self.tool_panel)

    def set_current_map_scale(self, map_scale: int):
        action = self.map_scale_actions.get(map_scale)

        if action is not None:
            action.setChecked(True)

    def set_measurement_mode(self, measurement_mode: MeasurementMode):
        if not isinstance(measurement_mode, MeasurementMode):
            raise TypeError("Invalid measurement mode.")

        distance_active = measurement_mode == MeasurementMode.DISTANCE

        angle_active = measurement_mode == MeasurementMode.ANGLE

        measurement_active = distance_active or angle_active

        self.distance_measurement_action.blockSignals(True)

        self.distance_measurement_action.setChecked(distance_active)

        self.distance_measurement_action.blockSignals(False)

        self.angle_measurement_action.blockSignals(True)

        self.angle_measurement_action.setChecked(angle_active)

        self.angle_measurement_action.blockSignals(False)

        if measurement_active:
            self._check_tool_action(None)

        else:
            self._restore_interaction_action()

    def _check_tool_action(self, interaction_mode: InteractionMode | None):
        """Checks the action of the given tool, or none for None,
        without triggering it."""

        self.interaction_action_group.setExclusive(False)

        for mode, action in self.tool_actions.items():
            action.blockSignals(True)

            action.setChecked(mode == interaction_mode)

            action.blockSignals(False)

        self.interaction_action_group.setExclusive(True)

    def _restore_interaction_action(self):
        self._check_tool_action(self.window.view.interaction_mode)

    def sync_tool_actions(self):
        """Checks the button of the active tool, or none while
        measuring."""

        if self.window.view.measurement_active:
            self._check_tool_action(None)

        else:
            self._restore_interaction_action()

    def set_measurement_alignment_enabled(self, enabled: bool):
        self.align_measurement_action.setEnabled(bool(enabled))

    def _activate_tool(self, interaction_mode: InteractionMode, checked: bool):
        if not checked:
            return

        was_measuring = self.window.view.measurement_active

        self.window.set_interaction_mode(interaction_mode)

        # Only end measuring if it was on, so the status bar keeps
        # showing the newly selected tool otherwise.
        if was_measuring:
            self.window.set_measurement_mode(MeasurementMode.INACTIVE)

    def _toggle_distance_measurement(self, checked: bool):
        if checked:
            self.angle_measurement_action.setChecked(False)

            self.window.set_measurement_mode(MeasurementMode.DISTANCE)

            return

        if self.window.measurement_coordinator.mode == MeasurementMode.DISTANCE:
            self.window.set_measurement_mode(MeasurementMode.INACTIVE)

    def _toggle_angle_measurement(self, checked: bool):
        if checked:
            self.distance_measurement_action.setChecked(False)

            self.window.set_measurement_mode(MeasurementMode.ANGLE)

            return

        if self.window.measurement_coordinator.mode == MeasurementMode.ANGLE:
            self.window.set_measurement_mode(MeasurementMode.INACTIVE)
