from dataclasses import replace

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QAction, QActionGroup, QGuiApplication, QKeySequence
from PySide6.QtWidgets import QMainWindow, QMenu, QSizePolicy, QToolBar, QToolButton, QWidget

from autodrive_editor.error_log import set_debug_logging
from autodrive_editor.i18n import tr
from autodrive_editor.terrain.background_map import Background
from autodrive_editor.ui.actions.shortcuts import ShortcutRegistry
from autodrive_editor.ui.actions.tool_catalog import (
    GENERATE_TASKS,
    GENERATE_TOOL,
    MERGED_TOOLS,
    TOOL_GROUPS,
    MergedTool,
    ToolDefinition,
    history_icon,
    merged_tool_of,
    tool_icon,
    tool_tooltip,
    variant_text,
)
from autodrive_editor.ui.controls.grid_controls import GridControls
from autodrive_editor.ui.controls.rotation_controls import RotationControls
from autodrive_editor.ui.dialogs.help_dialogs import (
    open_log_folder,
    show_about,
    show_version_history,
)
from autodrive_editor.ui.tools.generate_tool import GenerateTask
from autodrive_editor.ui.tools.interaction_mode import InteractionMode

TOOLBAR_ICON_SIZE = QSize(28, 28)
TOOLBAR_GAP_WIDTH = 8

# Entries of View → Show by Visibility field, in groups. "marker_names" is its own setting.
SHOW_GROUPS = (
    (("nodes", tr("Nodes")), ("node_ids", tr("Node IDs"))),
    (
        ("regular_connections", tr("Regular connections")),
        ("dual_connections", tr("Dual connections")),
        ("reverse_connections", tr("Reverse connections")),
    ),
    (
        ("markers", tr("Markers")),
        ("marker_names", tr("Marker names")),
        ("parking", tr("Parking positions")),
        ("sheds", tr("Sheds")),
        ("stations", tr("Stations")),
        ("drivability", tr("Drivability map")),
    ),
    (("hidden_selectable", tr("Hidden items can be selected")),),
)


class MainWindowActions:
    """Creates the window's actions, menus, toolbars and tool panel, and keeps the tool buttons in
    sync with the active tool.
    """

    def __init__(self, window: QMainWindow):
        self.window = window

        self._create_actions()
        self._create_tool_strip()
        self._create_show_actions()
        self._create_menu_bar()
        self._create_quick_access_toolbar()
        self._create_shortcut_registry()
        self.apply_shortcuts(window.settings.shortcuts)

    def _create_shortcut_registry(self):
        """All actions whose shortcut can be changed, grouped like the menus. The names are
        stored in the settings, so they must not change."""

        self.shortcuts = ShortcutRegistry()
        tools = tr("Tools")

        for mode, action in self.tool_actions.items():
            self.shortcuts.add(f"tool_{mode.name.lower()}", tools, action)

        self.shortcuts.add(
            "align_measurement",
            tools,
            self.align_measurement_action,
            self.align_measurement_action.toolTip(),
        )

        groups = (
            (
                tr("File"),
                ("open", "save_xml", "save_xml_as", "load_route", "settings", "exit"),
            ),
            (
                tr("Edit"),
                ("undo", "redo", "copy", "cut", "paste", "paste_at_original")
                + ("delete_selection", "grid_snap", "planning_mode"),
            ),
            (
                tr("View"),
                (
                    "display_options",
                    "background_overview",
                    "background_ground",
                    "background_picture",
                )
                + ("reset_view", "reset_rotation"),
            ),
            (tr("Check"), ("check_network",)),
            (tr("Generate"), ("building_types",)),
            (tr("Help"), ("version_history", "check_updates", "open_log_folder", "about")),
        )

        for group, names in groups:
            for name in names:
                self.shortcuts.add(name, group, getattr(self, f"{name}_action"))

        view = tr("View")
        docks = (self.window.inspector_dock, self.window.marker_dock, self.window.check_dock)

        for dock in docks:
            self.shortcuts.add(f"panel_{dock.objectName()}", view, dock.toggleViewAction())

        self.shortcuts.add(
            "panel_debug_dock", tr("Help"), self.window.debug_dock.toggleViewAction()
        )

        self.shortcuts.add("show_marker_names", view, self.marker_names_action)

        for name, action in self.show_actions.items():
            self.shortcuts.add(f"show_{name}", view, action)

    def apply_shortcuts(self, changed: dict[str, list[str]]):
        """Sets the stored shortcuts and shows them in the tool tooltips."""

        self.shortcuts.apply(changed)

        for mode, definition in self.tool_definitions.items():
            action = self.tool_actions[mode]
            shortcut = action.shortcut().toString(QKeySequence.NativeText)
            action.setToolTip(tool_tooltip(action.text(), shortcut, definition.description))

        for tool in MERGED_TOOLS:
            self._show_current_variant(tool)

        self.show_generate_task(self.current_generate_task)

    def _create_actions(self):
        # One exclusive group for all map tools, so exactly one tool
        # is active. The measuring tools un-check it while measuring.
        self.tool_actions: dict[InteractionMode, QAction] = {}
        self.tool_definitions: dict[InteractionMode, ToolDefinition] = {}

        for group in TOOL_GROUPS:
            for entry in group:
                if isinstance(entry, MergedTool):
                    for variant in entry.variants:
                        self._create_tool_action(variant, variant_text(entry, variant))

                else:
                    self._create_tool_action(entry)

        self.selection_action = self.tool_actions[InteractionMode.SELECT]
        self.generate_action = self.tool_actions[InteractionMode.GENERATE]

        self.interaction_action_group = QActionGroup(self.window)

        self.interaction_action_group.setExclusive(True)

        for interaction_mode, action in self.tool_actions.items():
            self.interaction_action_group.addAction(action)

            action.triggered.connect(
                lambda checked, mode=interaction_mode: self._activate_tool(mode, checked)
            )

        self.selection_action.setChecked(True)

        # One strip button per merged tool: it shows the current variant and activates it.
        # The variant actions themselves are the buttons in the options bar.
        self.merged_tool_actions: dict[MergedTool, QAction] = {}
        self.current_variants: dict[MergedTool, InteractionMode] = {}

        for tool in MERGED_TOOLS:
            action = QAction(tool.text, self.window)
            action.setCheckable(True)
            action.triggered.connect(lambda checked, tool=tool: self._activate_merged_tool(tool))
            self.merged_tool_actions[tool] = action
            self.current_variants[tool] = tool.modes[0]

        # The tasks of the Generate tool: buttons in its options bar and entries of the
        # Generate menu.
        self.generate_task_actions: dict[GenerateTask, QAction] = {}
        self.current_generate_task = GenerateTask.ROUTE
        task_group = QActionGroup(self.window)

        for task, (icon, description) in GENERATE_TASKS.items():
            action = QAction(tool_icon(icon), task.display_name, self.window)
            action.setCheckable(True)
            action.setToolTip(tool_tooltip(self._generate_task_text(task), "", description))
            action.setStatusTip(description)
            action.triggered.connect(lambda checked, task=task: self.window.set_generate_task(task))
            task_group.addAction(action)
            self.generate_task_actions[task] = action

        self.align_measurement_action = QAction(
            tool_icon("measure_align"), tr("Align view to line"), self.window
        )

        self.align_measurement_action.setToolTip(tr("Align the measuring line horizontally"))

        self.align_measurement_action.setStatusTip(
            tr("Rotate the view so that point A is on the left and point B on the right")
        )

        self.align_measurement_action.setEnabled(False)

        self.align_measurement_action.triggered.connect(self.window.align_view_to_measurement)

        self.open_action = QAction(tool_icon("open"), tr("Open…"), self.window)
        self.open_action.setShortcut(QKeySequence.Open)
        self.open_action.setStatusTip(tr("Open a route, a savegame or an AutoDrive XML file"))
        self.open_action.triggered.connect(self.window.files.open)

        self.save_xml_action = QAction(tool_icon("save"), tr("Save"), self.window)
        self.save_xml_action.setShortcut(QKeySequence.Save)
        self.save_xml_action.setStatusTip(tr("Save the AutoDrive data into the loaded file"))
        self.save_xml_action.setEnabled(False)
        self.save_xml_action.triggered.connect(self.window.files.save_xml)

        # Named save_xml_as, so shortcuts stored for "Save as…" still apply.
        self.save_xml_as_action = QAction(tr("Save as route…"), self.window)
        self.save_xml_as_action.setShortcut(QKeySequence("Ctrl+Shift+S"))
        self.save_xml_as_action.setStatusTip(
            tr("Keep a version of the network as a route in the RoutesManager")
        )
        self.save_xml_as_action.setEnabled(False)
        self.save_xml_as_action.triggered.connect(self.window.files.save_as_route)

        self.load_route_action = QAction(tr("Load route into savegame…"), self.window)
        self.load_route_action.setStatusTip(
            tr("Replace the savegame's network with a route of the RoutesManager")
        )
        self.load_route_action.setEnabled(False)
        self.load_route_action.triggered.connect(self.window.files.load_route_into_savegame)

        self.settings_action = QAction(tr("Settings…"), self.window)

        self.settings_action.triggered.connect(self.window.open_settings)

        self.exit_action = QAction(tr("Exit"), self.window)

        self.exit_action.triggered.connect(self.window.close)

        self.about_action = QAction(tr("About AutoDrive FS25 Editor"), self.window)

        self.about_action.triggered.connect(lambda: show_about(self.window))

        self.version_history_action = QAction(tr("Version history"), self.window)

        self.version_history_action.triggered.connect(lambda: show_version_history(self.window))

        self.check_updates_action = QAction(tr("Check for updates"), self.window)

        self.check_updates_action.triggered.connect(self.window.updates.check_now)

        self.open_log_folder_action = QAction(tr("Open log folder"), self.window)

        self.open_log_folder_action.setStatusTip(tr("Show the editor's log file in Explorer"))

        self.open_log_folder_action.triggered.connect(open_log_folder)

        self.debug_log_action = QAction(tr("Debug log"), self.window)
        self.debug_log_action.setCheckable(True)
        self.debug_log_action.setStatusTip(
            tr("Write detailed entries to the log file, e.g. for each route search")
        )
        self.debug_log_action.setChecked(self.window.settings.debug_log)
        self.debug_log_action.toggled.connect(self._set_debug_log)

        self.display_options_action = QAction(tr("Display options…"), self.window)

        self.display_options_action.triggered.connect(self.window.open_display_options)

        self.building_types_action = QAction(tr("Building types…"), self.window)

        self.building_types_action.setStatusTip(
            tr("Choose the group of each building type and which ones are shown")
        )

        self.building_types_action.triggered.connect(self.window.open_building_types)

        self.background_action_group = QActionGroup(self.window)
        self.background_overview_action = self._background_action(
            Background.OVERVIEW, tr("Overview"), tr("Show the map image of the map mod")
        )
        self.background_ground_action = self._background_action(
            Background.GROUND,
            tr("Ground map"),
            tr(
                "Show the map drawn from its ground textures, with the fields, instead of the "
                "map image. Maps imported with an older version need to be imported again."
            ),
        )
        self.background_picture_action = self._background_action(
            Background.PICTURE,
            tr("Game picture"),
            tr("Show the map as the game draws it from above, captured with the companion mod"),
        )
        self.background_actions = {
            Background.OVERVIEW: self.background_overview_action,
            Background.GROUND: self.background_ground_action,
            Background.PICTURE: self.background_picture_action,
        }

        self.reset_view_action = QAction(tr("Reset view"), self.window)

        self.reset_view_action.setEnabled(False)

        self.reset_rotation_action = QAction(tr("Reset rotation"), self.window)

        self.reset_rotation_action.setEnabled(False)

        self.reset_rotation_action.triggered.connect(self.window.reset_view_rotation)

        self.capture_picture_action = QAction(tr("Capture game picture…"), self.window)
        self.capture_picture_action.setStatusTip(
            tr("Let the game render the whole map from above, with the companion mod")
        )
        self.capture_picture_action.triggered.connect(self.window.picture_capture.open_dialog)

        self.refresh_picture_action = QAction(
            tool_icon("picture_refresh"), tr("Refresh game picture tiles"), self.window
        )
        self.refresh_picture_action.setCheckable(True)
        self.refresh_picture_action.setEnabled(False)
        self.refresh_picture_action.setStatusTip(
            tr("Mark tiles of the game picture and let the game render them again")
        )
        self.refresh_picture_action.toggled.connect(self.window.picture_capture.set_refresh_active)

        self.check_network_action = QAction(tr("Check network"), self.window)
        self.check_network_action.setStatusTip(
            tr("Find overlapping nodes, nodes outside the map, wrong heights and bad connections")
        )
        self.check_network_action.triggered.connect(self.window.network_check.run)

        self._create_undo_actions()
        self._create_delete_selection_action()

        self._create_clipboard_actions()

        self.grid_snap_action = QAction(tool_icon("grid_snap"), tr("Snap to grid"), self.window)
        self.grid_snap_action.setCheckable(True)
        self.grid_snap_action.setShortcut(QKeySequence("S"))
        self.grid_snap_action.toggled.connect(
            lambda enabled: self.window.grid_coordinator.set_grid_snap_enabled(enabled)
        )

        self.planning_mode_action = self.window.planning.action

    def _background_action(self, background: Background, label: str, tip: str) -> QAction:
        action = QAction(label, self.window)
        action.setCheckable(True)
        action.setChecked(background == self.window.settings.background)
        # The others are enabled once a map that has them is loaded.
        action.setEnabled(background == Background.OVERVIEW)
        action.setStatusTip(tip)
        action.toggled.connect(
            lambda checked: self.window.set_background(background) if checked else None
        )
        self.background_action_group.addAction(action)

        return action

    def _set_debug_log(self, enabled: bool):
        self.window.settings.set_debug_log(enabled)
        set_debug_logging(enabled)

    UNDO_TEXT = tr("Undo")
    REDO_TEXT = tr("Redo")

    def _create_tool_action(self, definition: ToolDefinition, text: str | None = None) -> QAction:
        action = QAction(tool_icon(definition.icon), text or definition.text, self.window)

        action.setCheckable(True)

        # The tooltip with the shortcut is set by apply_shortcuts.
        action.setShortcut(QKeySequence(definition.shortcut))

        action.setStatusTip(definition.description)

        # Added to the window so the shortcut also works while the
        # tool panel is hidden.
        self.window.addAction(action)

        self.tool_actions[definition.interaction_mode] = action
        self.tool_definitions[definition.interaction_mode] = definition

        return action

    def _create_undo_actions(self):
        edit_history = self.window.edit_history
        undo_group = edit_history.undo_group

        self.undo_action = self._create_history_action(
            icon="undo",
            base_text=self.UNDO_TEXT,
            shortcut=QKeySequence.Undo,
            trigger=self.window.undo,
            can_run_changed=undo_group.canUndoChanged,
            text_changed=undo_group.undoTextChanged,
        )

        # A junction being drawn and Find route waypoints can be undone even with nothing in the
        # history.
        junction = self.window.junction_operation
        find_route = self.window.find_route_operation

        def update_undo():
            self.undo_action.setEnabled(
                undo_group.canUndo()
                or junction.preview is not None
                or find_route.can_undo_waypoints
            )

        undo_group.canUndoChanged.connect(update_undo)
        junction.preview_changed.connect(update_undo)
        find_route.preview_changed.connect(update_undo)

        self.redo_action = self._create_history_action(
            icon="redo",
            base_text=self.REDO_TEXT,
            shortcut=QKeySequence.Redo,
            trigger=edit_history.redo,
            can_run_changed=undo_group.canRedoChanged,
            text_changed=undo_group.redoTextChanged,
        )

        style_hints = QGuiApplication.styleHints()
        style_hints.colorSchemeChanged.connect(self._update_history_icons)
        self._update_history_icons(style_hints.colorScheme())

    def _update_history_icons(self, color_scheme: Qt.ColorScheme):
        dark = color_scheme == Qt.ColorScheme.Dark
        self.undo_action.setIcon(history_icon("undo", dark))
        self.redo_action.setIcon(history_icon("redo", dark))

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

        file_menu.addAction(self.open_action)

        self.recent_menu = file_menu.addMenu(tr("Open recent"))

        self.recent_menu.aboutToShow.connect(self.fill_recent_menu)

        file_menu.addAction(self.save_xml_action)

        file_menu.addAction(self.save_xml_as_action)

        file_menu.addAction(self.load_route_action)

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

        edit_menu.addSeparator()

        edit_menu.addAction(self.planning_mode_action)

        view_menu = menu_bar.addMenu(tr("View"))

        view_menu.addAction(self.display_options_action)

        background_menu = view_menu.addMenu(tr("Background"))

        for action in self.background_actions.values():
            background_menu.addAction(action)

        background_menu.addAction(self.capture_picture_action)
        background_menu.addAction(self.refresh_picture_action)

        view_menu.addSeparator()

        view_menu.addAction(self.window.inspector_dock.toggleViewAction())

        view_menu.addAction(self.window.marker_dock.toggleViewAction())

        view_menu.addAction(self.window.check_dock.toggleViewAction())

        view_menu.addSeparator()

        show_menu = view_menu.addMenu(tr("Show"))

        for index, group in enumerate(SHOW_GROUPS):
            if index > 0:
                show_menu.addSeparator()

            for name, _ in group:
                show_menu.addAction(
                    self.marker_names_action if name == "marker_names" else self.show_actions[name]
                )

        view_menu.addSeparator()

        view_menu.addAction(self.reset_view_action)

        view_menu.addAction(self.reset_rotation_action)

        check_menu = menu_bar.addMenu(tr("Check"))

        check_menu.addAction(self.check_network_action)

        generate_menu = menu_bar.addMenu(tr("Generate"))

        generate_menu.addActions(list(self.generate_task_actions.values()))
        generate_menu.addSeparator()
        generate_menu.addAction(self.building_types_action)

        help_menu = menu_bar.addMenu(tr("Help"))

        help_menu.addAction(self.version_history_action)

        help_menu.addAction(self.check_updates_action)

        help_menu.addSeparator()
        help_menu.addAction(self.window.debug_dock.toggleViewAction())
        help_menu.addAction(self.debug_log_action)
        help_menu.addAction(self.open_log_folder_action)

        help_menu.addSeparator()

        help_menu.addAction(self.about_action)

    def fill_recent_menu(self):
        """Fills File → Open recent from the settings each time it opens."""

        files = self.window.files
        items = files.settings.recent_items

        self.recent_menu.clear()

        for item in items:
            action = self.recent_menu.addAction(item.label)
            action.setStatusTip(item.path)
            action.triggered.connect(lambda checked=False, item=item: files.open_recent(item))

        if not items:
            self.recent_menu.addAction(tr("No recent files")).setEnabled(False)

        self.recent_menu.addSeparator()

        clear_action = self.recent_menu.addAction(tr("Clear list"))
        clear_action.setEnabled(bool(items))
        clear_action.triggered.connect(files.clear_recent_items)

    def _create_quick_access_toolbar(self):
        self.quick_access_toolbar = QToolBar(tr("Quick access"), self.window)

        self.quick_access_toolbar.setObjectName("quick_access_toolbar")

        self.quick_access_toolbar.setMovable(False)

        self.quick_access_toolbar.setFloatable(False)

        self.quick_access_toolbar.setToolButtonStyle(Qt.ToolButtonIconOnly)

        self.quick_access_toolbar.setIconSize(TOOLBAR_ICON_SIZE)

        self.window.addToolBar(Qt.TopToolBarArea, self.quick_access_toolbar)

        self.quick_access_toolbar.addAction(self.open_action)
        self.quick_access_toolbar.addAction(self.save_xml_action)
        self._add_toolbar_gap()

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

        for action in (self.copy_action, self.cut_action, self.paste_action):
            self.quick_access_toolbar.addAction(action)

        spacer = QWidget(self.quick_access_toolbar)

        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        self.quick_access_toolbar.addWidget(spacer)

        # The three backgrounds, as in View → Background.
        self.background_button = QToolButton(self.quick_access_toolbar)
        self.background_button.setToolTip(tr("Background"))
        self.background_button.setPopupMode(QToolButton.InstantPopup)
        background_menu = QMenu(self.background_button)
        background_menu.addActions(list(self.background_actions.values()))
        self.background_button.setMenu(background_menu)
        self._show_as_icon(self.background_button, "background")
        self.quick_access_toolbar.addWidget(self.background_button)

        self.rotation_controls = RotationControls(
            rotation_angle=self.window.view.rotation_angle,
            rotation_step=self.window.view.rotation_step,
            parent=self.quick_access_toolbar,
        )

        self.rotation_controls.rotation_angle_requested.connect(self.window.set_view_rotation)

        self.rotation_controls.rotation_step_requested.connect(self.window.set_view_rotation_step)

        self.rotation_controls.reset_requested.connect(self.window.reset_view_rotation)

        self._show_as_icon(self.rotation_controls, "view_rotation")

        self.grid_controls = GridControls(
            grid_visible=self.window.background_map.grid_visible,
            grid_spacing=self.window.background_map.grid_spacing,
            grid_rotation=self.window.background_map.grid_rotation,
            parent=self.quick_access_toolbar,
        )

        self._show_as_icon(self.grid_controls, "grid")

        self.quick_access_toolbar.addWidget(self.grid_controls)

        self.quick_access_toolbar.addAction(self.grid_snap_action)

        self.quick_access_toolbar.addWidget(self.rotation_controls)

        self.quick_access_toolbar.addAction(self.refresh_picture_action)

        # A mode, not a tool: at the far right, apart from the tools.
        self.quick_access_toolbar.addSeparator()

        self.quick_access_toolbar.addAction(self.planning_mode_action)

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

    def _create_tool_strip(self):
        """The fixed one-column strip of all tools at the left, icons only."""

        self.tool_strip = QToolBar(tr("Tools"), self.window)
        self.tool_strip.setObjectName("tool_strip")
        self.tool_strip.setMovable(False)
        self.tool_strip.setFloatable(False)
        self.tool_strip.setOrientation(Qt.Vertical)
        self.tool_strip.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self.tool_strip.setIconSize(TOOLBAR_ICON_SIZE)
        # Not listed in the toolbar context menu, so it cannot be hidden.
        self.tool_strip.toggleViewAction().setVisible(False)

        for index, group in enumerate(TOOL_GROUPS):
            if index:
                self.tool_strip.addSeparator()

            for entry in group:
                if isinstance(entry, MergedTool):
                    self.tool_strip.addAction(self.merged_tool_actions[entry])
                else:
                    self.tool_strip.addAction(self.tool_actions[entry.interaction_mode])

        self.window.addToolBar(Qt.LeftToolBarArea, self.tool_strip)

    def _create_show_actions(self):
        self.marker_names_action = QAction(tr("Marker names"), self.window)
        self.marker_names_action.setCheckable(True)
        self.marker_names_action.setChecked(self.window.settings.marker_names_visible)
        self.marker_names_action.toggled.connect(self.window.set_marker_names_visible)

        visibility = self.window.scene_renderer.visibility
        self.show_actions: dict[str, QAction] = {}

        for group in SHOW_GROUPS:
            for name, label in group:
                if name == "marker_names":
                    continue

                action = QAction(label, self.window)
                action.setCheckable(True)
                action.setChecked(getattr(visibility, name))
                action.toggled.connect(lambda checked, name=name: self._set_shown(name, checked))
                self.show_actions[name] = action

    def _set_shown(self, name: str, shown: bool):
        visibility = self.window.scene_renderer.visibility

        self.window.set_visibility(replace(visibility, **{name: shown}))

    def _check_tool_action(self, interaction_mode: InteractionMode | None):
        """Checks the action of the given tool, or none for None,
        without triggering it."""

        self.interaction_action_group.setExclusive(False)

        for mode, action in self.tool_actions.items():
            action.blockSignals(True)

            action.setChecked(mode == interaction_mode)

            action.blockSignals(False)

        self.interaction_action_group.setExclusive(True)

        for tool, action in self.merged_tool_actions.items():
            action.setChecked(interaction_mode in tool.modes)

    def sync_tool_actions(self):
        """Checks the button of the active tool."""

        mode = self.window.view.interaction_mode
        tool = merged_tool_of(mode)

        if tool is not None:
            self.current_variants[tool] = mode
            self._show_current_variant(tool)

        self._check_tool_action(mode)

    def set_measurement_alignment_enabled(self, enabled: bool):
        self.align_measurement_action.setEnabled(bool(enabled))

    def _show_current_variant(self, tool: MergedTool):
        """The strip button of a merged tool shows the icon and tooltip of its current variant."""

        variant = self.tool_actions[self.current_variants[tool]]
        action = self.merged_tool_actions[tool]
        action.setIcon(variant.icon())
        action.setToolTip(variant.toolTip())
        action.setStatusTip(variant.statusTip())

    @staticmethod
    def _generate_task_text(task: GenerateTask) -> str:
        return f"{GENERATE_TOOL.text} – {task.display_name}"

    def show_generate_task(self, task: GenerateTask):
        """Checks the task's button; the Generate button shows the task's icon and tooltip."""

        self.current_generate_task = task
        self.generate_task_actions[task].setChecked(True)
        shortcut = self.generate_action.shortcut().toString(QKeySequence.NativeText)
        self.generate_action.setIcon(self.generate_task_actions[task].icon())
        self.generate_action.setToolTip(
            tool_tooltip(self._generate_task_text(task), shortcut, GENERATE_TASKS[task][1])
        )

    def _activate_merged_tool(self, tool: MergedTool):
        self._activate_tool(self.current_variants[tool], True)
        # A click on the active tool un-checks its button; check it again.
        self.sync_tool_actions()

    def _activate_tool(self, interaction_mode: InteractionMode, checked: bool):
        if not checked:
            return

        self.window.set_interaction_mode(interaction_mode)
