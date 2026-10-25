from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFileDialog, QGraphicsScene, QLabel, QMainWindow

from autodrive_editor.editing.commands.edit_command import DataChange
from autodrive_editor.editing.edit_history import EditHistory
from autodrive_editor.editing.operations.connect_nodes import ConnectNodesOperation
from autodrive_editor.editing.operations.create_nodes import CreateNodesOperation
from autodrive_editor.editing.operations.delete_nodes import DeleteNodesOperation
from autodrive_editor.editing.operations.move_nodes import MoveNodesOperation
from autodrive_editor.editing.operations.node_types import NodeTypeOperation
from autodrive_editor.editing.operations.rotate_selection import RotateSelectionOperation
from autodrive_editor.file_io.project_file import ProjectFileStore
from autodrive_editor.measurement.controller import MeasurementController
from autodrive_editor.measurement.coordinator import MeasurementCoordinator
from autodrive_editor.measurement.mode import MeasurementMode
from autodrive_editor.model.autodrive_data import (
    REGULAR_FLAG,
    SUBPRIO_FLAG,
    AutoDriveData,
    NodeData,
)
from autodrive_editor.model.connections import ConnectionType
from autodrive_editor.paths import LOCAL_PROJECTS_DIRECTORY, MARKER_ICON_PATH
from autodrive_editor.project.project_coordinator import ProjectCoordinator
from autodrive_editor.rendering.display_style import DisplayStyle
from autodrive_editor.rendering.scene_renderer import SceneRenderer
from autodrive_editor.selection.node_selection import NodeSelection
from autodrive_editor.selection.selection_coordinator import SelectionCoordinator
from autodrive_editor.settings.app_settings import AppSettings
from autodrive_editor.terrain.background_map import BackgroundMap
from autodrive_editor.terrain.heightmap import Heightmap
from autodrive_editor.ui.actions.main_window_actions import MainWindowActions
from autodrive_editor.ui.controls.grid_coordinator import GridCoordinator
from autodrive_editor.ui.dialogs.settings_dialog import SettingsDialog
from autodrive_editor.ui.map_view.map_view import MapView
from autodrive_editor.ui.map_view.rotation_controller import ViewRotationController
from autodrive_editor.ui.panels.debug_dock import DebugDock
from autodrive_editor.ui.panels.debug_dock_coordinator import DebugDockCoordinator
from autodrive_editor.ui.panels.display_options_dialog import DisplayOptionsDialog
from autodrive_editor.ui.panels.node_info_formatter import NodeInfoFormatter
from autodrive_editor.ui.tools.connect_nodes_tool import ConnectNodesTool
from autodrive_editor.ui.tools.create_node_tool import CreateNodeTool
from autodrive_editor.ui.tools.delete_nodes_tool import DeleteNodesTool
from autodrive_editor.ui.tools.interaction_mode import InteractionMode
from autodrive_editor.ui.tools.measure_tool import MeasureTool
from autodrive_editor.ui.tools.move_nodes_tool import MoveNodesTool
from autodrive_editor.ui.tools.rotate_selection_tool import RotateSelectionTool
from autodrive_editor.ui.tools.select_tool import SelectTool
from autodrive_editor.ui.tools.toggle_node_type_tool import ToggleNodeTypeTool


class MainWindow(QMainWindow):
    """The editor window. It creates all parts of the editor and wires
    them together:

    1. scene and map view
    2. map layers: background, heightmap, renderer, project files
    3. selection and measurement
    4. edit history and edit operations, then the map tools using them
    5. project coordinator, which loads data into all of the above
    6. widgets, actions, menus and toolbars, then the signal wiring
    """

    WINDOW_TITLE = "AutoDrive FS25 Editor"
    INITIAL_WIDTH = 1400
    INITIAL_HEIGHT = 900

    NO_FILE_STATUS = "Keine Datei geladen"
    NO_SELECTION_INFO = "Keine Node ausgewählt"

    DEFAULT_MAP_SCALE = 1

    def __init__(self):
        super().__init__()

        self.local_projects_directory = LOCAL_PROJECTS_DIRECTORY

        # Detects the FS25 folder on first start and keeps it afterwards.
        self.settings = AppSettings()
        self.settings.ensure_game_folder()

        self._configure_window()
        self._create_scene_and_view()

        self._create_map_layers()
        self._create_selection_and_measurement()
        self._create_edit_operations()
        self._register_map_tools()
        self._create_project_coordinator()

        self._create_status_widgets()
        self._create_central_widget()
        self._create_debug_dock()

        self.actions = MainWindowActions(self)
        self.actions.set_current_map_scale(self.background_map.map_scale)

        self._create_grid_coordinator()
        self._connect_signals()

        # Created after the renderer is connected to the view, so the
        # dock reads the renderer state after it has been updated.
        self._create_debug_dock_coordinator()

    def select_background(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "overview.dds auswählen", "", "DDS-Bilder (*.dds);;Alle Dateien (*)"
        )

        if not filename:
            return

        try:
            self.project_coordinator.load_background_file(filename)

        except Exception as ex:
            self._set_status(f"DDS konnte nicht geladen werden: {ex}")

    def select_heightmap(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "dem.png auswählen", "", "PNG-Heightmaps (*.png);;Alle Dateien (*)"
        )

        if not filename:
            return

        try:
            self.project_coordinator.load_heightmap_file(filename)

        except Exception as ex:
            self._set_status(f"Heightmap konnte nicht geladen werden: {ex}")

    def remove_heightmap(self):
        self.project_coordinator.remove_heightmap()

    def set_map_scale(self, map_scale: int):
        action = self.actions.map_scale_actions.get(map_scale)

        map_scale_label = action.text() if action is not None else str(map_scale)

        try:
            self.project_coordinator.set_map_scale(
                map_scale=map_scale, map_scale_label=map_scale_label
            )

        except Exception as ex:
            self._set_status(f"Kartengröße konnte nicht geändert werden: {ex}")

    def load_xml(self):
        filename, _ = QFileDialog.getOpenFileName(self, "AutoDrive XML öffnen", "", "XML (*.xml)")

        if not filename:
            return

        try:
            self.project_coordinator.load_xml_file(filename)

        except Exception as ex:
            self._set_status(f"XML konnte nicht geladen werden: {ex}")

    def load_xml_file(self, filename):
        self.project_coordinator.load_xml_file(filename)

    def save_project(self):
        if not self.project_coordinator.current_xml_path:
            self._set_status("Bitte zuerst eine AutoDrive-XML laden")
            return

        default_path = (
            self.project_coordinator.current_config_path
            if self.project_coordinator.current_config_path
            else str(self.local_projects_directory)
        )

        config_path, _ = QFileDialog.getSaveFileName(
            self, "Projektkonfiguration speichern", default_path, "JSON-Konfiguration (*.json)"
        )

        if not config_path:
            return

        if not config_path.lower().endswith(".json"):
            config_path += ".json"

        try:
            self.project_coordinator.save_project_file(config_path)

        except Exception as ex:
            self._set_status(f"Projekt konnte nicht gespeichert werden: {ex}")

    def load_project(self):
        config_path, _ = QFileDialog.getOpenFileName(
            self,
            "Projektkonfiguration öffnen",
            str(self.local_projects_directory),
            "JSON-Konfiguration (*.json)",
        )

        if not config_path:
            return

        try:
            self.project_coordinator.load_project_file(config_path)

        except Exception as ex:
            self._set_status(f"Projekt konnte nicht geladen werden: {ex}")

    def show_node_info(self, node_data: NodeData):
        self.selection_coordinator.show_node_info(node_data)

    def set_interaction_mode(self, interaction_mode: InteractionMode):
        self.view.set_interaction_mode(interaction_mode)

        status_text = f"Modus: {interaction_mode.display_name}"

        status_hint = self.view.active_tool.status_hint()

        if status_hint:
            status_text += f" – {status_hint}"

        self._set_status(status_text)

    def set_view_rotation(self, rotation_angle: float):
        self.view.set_rotation_angle(rotation_angle)

        self._set_status(f"Rotation: {self.view.rotation_angle:.2f}°")

    def set_view_rotation_step(self, rotation_step: float):
        self.view.set_rotation_step(rotation_step)

        self._set_status(f"Rotationsraster: {self.view.rotation_step:.2f}°")

    def reset_view_rotation(self):
        self.view.reset_view_rotation()

        self._set_status("Rotation zurückgesetzt")

    def set_measurement_mode(self, measurement_mode: MeasurementMode):
        self.measurement_coordinator.set_mode(measurement_mode)

    def delete_selection(self):
        self.delete_nodes_operation.delete_selection()

    def align_view_to_measurement(self):
        self.measurement_coordinator.align_view_to_measurement()

    def open_settings(self):
        dialog = SettingsDialog(self.settings, parent=self)

        if dialog.exec():
            folder = self.settings.game_folder

            if folder is None:
                self._set_status("Kein Spielordner gesetzt")
            elif folder.is_valid:
                self._set_status(f"Spielordner: {folder.path}")
            else:
                self._set_status(f"Spielordner ist kein FS25-Benutzerordner: {folder.path}")

    def open_display_options(self):
        dialog = DisplayOptionsDialog(display_style=self.scene_renderer.display_style, parent=self)

        dialog.style_applied.connect(self.apply_display_style)

        dialog.exec()

    def apply_display_style(self, display_style: DisplayStyle):
        if not isinstance(display_style, DisplayStyle):
            raise TypeError("Der Darstellungsstil ist ungültig.")

        self.scene_renderer.set_display_style(display_style)

        self.project_coordinator.rebuild_scene_after_style_change()

    def _configure_window(self):
        # Qt shows "*" in place of "[*]" while the window is modified.
        self.setWindowTitle(f"{self.WINDOW_TITLE}[*]")

        self.resize(self.INITIAL_WIDTH, self.INITIAL_HEIGHT)

    def _create_scene_and_view(self):
        self.scene = QGraphicsScene()

        self.view = MapView()

        self.view.setScene(self.scene)

    def _create_map_layers(self):
        """Background map, heightmap, node rendering and project files."""

        self.background_map = BackgroundMap(self.scene, map_scale=self.DEFAULT_MAP_SCALE)

        self.heightmap = Heightmap()

        self.node_info_formatter = NodeInfoFormatter(
            background_map=self.background_map, heightmap=self.heightmap
        )

        self.scene_renderer = SceneRenderer(self.scene, MARKER_ICON_PATH)

        self.project_files = ProjectFileStore(self.local_projects_directory)

    def _create_selection_and_measurement(self):
        self.node_selection = NodeSelection()

        self.selection_coordinator = SelectionCoordinator(
            view=self.view,
            renderer=self.scene_renderer,
            node_selection=self.node_selection,
            node_info_formatter=self.node_info_formatter,
            autodrive_data_provider=self._get_autodrive_data,
            parent=self,
        )

        self.measurement_controller = MeasurementController(scene=self.scene, parent=self)

        self.measurement_coordinator = MeasurementCoordinator(
            view=self.view,
            controller=self.measurement_controller,
            node_item_provider=self.selection_coordinator.get_node_item_at,
            parent=self,
        )

    def _create_edit_operations(self):
        """The undo history and every operation that changes the data."""

        self.edit_history = EditHistory(parent=self)

        self.move_nodes_operation = MoveNodesOperation(
            view=self.view,
            selection_coordinator=self.selection_coordinator,
            node_selection=self.node_selection,
            edit_history=self.edit_history,
            autodrive_data_provider=self._get_autodrive_data,
            terrain_height_at=self._get_terrain_height,
            parent=self,
        )

        self.delete_nodes_operation = DeleteNodesOperation(
            selection_coordinator=self.selection_coordinator,
            node_selection=self.node_selection,
            edit_history=self.edit_history,
            autodrive_data_provider=self._get_autodrive_data,
            parent=self,
        )

        self.connect_nodes_operation = ConnectNodesOperation(
            selection_coordinator=self.selection_coordinator,
            edit_history=self.edit_history,
            autodrive_data_provider=self._get_autodrive_data,
            parent=self,
        )

        self.rotate_selection_operation = RotateSelectionOperation(
            node_selection=self.node_selection,
            edit_history=self.edit_history,
            autodrive_data_provider=self._get_autodrive_data,
            terrain_height_at=self._get_terrain_height,
            parent=self,
        )

        self.create_nodes_operation = CreateNodesOperation(
            view=self.view,
            selection_coordinator=self.selection_coordinator,
            edit_history=self.edit_history,
            autodrive_data_provider=self._get_autodrive_data,
            terrain_height_at=self._get_terrain_height,
            parent=self,
        )

        self.node_type_operation = NodeTypeOperation(
            selection_coordinator=self.selection_coordinator,
            node_selection=self.node_selection,
            edit_history=self.edit_history,
            autodrive_data_provider=self._get_autodrive_data,
            parent=self,
        )

    def _create_project_coordinator(self):
        self.project_coordinator = ProjectCoordinator(
            scene=self.scene,
            view=self.view,
            project_files=self.project_files,
            background_map=self.background_map,
            heightmap=self.heightmap,
            scene_renderer=self.scene_renderer,
            selection_coordinator=self.selection_coordinator,
            measurement_coordinator=self.measurement_coordinator,
            parent=self,
        )

    def _register_map_tools(self):
        self.view.register_tool(
            InteractionMode.SELECT, SelectTool(self.view, self.selection_coordinator)
        )

        for interaction_mode, flag in (
            (InteractionMode.CREATE_NODES, REGULAR_FLAG),
            (InteractionMode.CREATE_SUBPRIO_NODES, SUBPRIO_FLAG),
        ):
            self.view.register_tool(
                interaction_mode, CreateNodeTool(self.view, self.create_nodes_operation, flag)
            )

        self.view.register_tool(
            InteractionMode.TOGGLE_NODE_TYPE,
            ToggleNodeTypeTool(self.view, self.node_type_operation),
        )

        self.view.register_tool(
            InteractionMode.MOVE_NODES, MoveNodesTool(self.view, self.move_nodes_operation)
        )

        self.view.register_tool(
            InteractionMode.ROTATE_SELECTION,
            RotateSelectionTool(
                self.view,
                self.rotate_selection_operation,
                z_value=(self.scene_renderer.display_style.selected_node_z + 1),
            ),
        )

        self.view.register_tool(
            InteractionMode.DELETE_NODES, DeleteNodesTool(self.view, self.delete_nodes_operation)
        )

        connect_tools = (
            (InteractionMode.CONNECT_REGULAR, ConnectionType.REGULAR, "regular_connection_color"),
            (InteractionMode.CONNECT_DUAL, ConnectionType.DUAL, "dual_connection_color"),
            (InteractionMode.CONNECT_REVERSE, ConnectionType.REVERSE, "reverse_connection_color"),
        )

        for interaction_mode, connection_type, color_name in connect_tools:
            self.view.register_tool(
                interaction_mode,
                ConnectNodesTool(
                    self.view,
                    self.connect_nodes_operation,
                    connection_type,
                    color_provider=(
                        lambda name=color_name: getattr(self.scene_renderer.display_style, name)
                    ),
                    z_value=(self.scene_renderer.display_style.selected_node_z + 1),
                ),
            )

        self.view.register_measure_tool(MeasureTool(self.view, self.measurement_coordinator))

    def _create_grid_coordinator(self):
        self.grid_coordinator = GridCoordinator(
            background_map=self.background_map,
            grid_controls=self.actions.grid_controls,
            parent=self,
        )

    def _create_debug_dock_coordinator(self):
        self.debug_dock_coordinator = DebugDockCoordinator(
            debug_dock=self.debug_dock,
            view=self.view,
            scene_renderer=self.scene_renderer,
            parent=self,
        )

        self.selection_coordinator.selection_state_changed.connect(
            self.debug_dock_coordinator.refresh
        )

        self.project_coordinator.debug_refresh_requested.connect(
            self.debug_dock_coordinator.refresh
        )

    def _get_terrain_height(self, x: float, z: float) -> float | None:
        """Terrain height from the loaded heightmap, or None without
        heightmap or outside the map."""

        if not self.heightmap.has_heightmap():
            return None

        try:
            return self.heightmap.get_height_at(
                world_x=x, world_z=z, map_scale=self.background_map.map_scale
            ).height

        except ValueError:
            return None

    def _get_autodrive_data(self) -> AutoDriveData | None:
        return self.project_coordinator.autodrive_data

    def _create_status_widgets(self):
        self.status = QLabel(self.NO_FILE_STATUS)

        self.statusBar().addWidget(self.status, 1)

    def _create_central_widget(self):
        self.setCentralWidget(self.view)

    def _create_debug_dock(self):
        self.debug_dock = DebugDock(self)

        self.addDockWidget(Qt.RightDockWidgetArea, self.debug_dock)

        self.debug_dock.set_node_info(self.NO_SELECTION_INFO)

        self.debug_dock.hide()

    def _connect_signals(self):
        self.view.zoom_changed.connect(self.scene_renderer.update_visibility_for_zoom)

        self.view.visible_scene_rect_changed.connect(self.scene_renderer.update_visible_scene_rect)

        self.view.rotation_changed.connect(self._handle_rotation_changed)

        self.measurement_coordinator.status_changed.connect(self._set_status)

        self.measurement_coordinator.measurement_mode_changed.connect(
            self.actions.set_measurement_mode
        )

        self.measurement_coordinator.alignment_available_changed.connect(
            self.actions.set_measurement_alignment_enabled
        )

        self.selection_coordinator.selection_info_changed.connect(self.debug_dock.set_node_info)

        self.project_coordinator.status_changed.connect(self._set_status)

        self.grid_coordinator.status_changed.connect(self._set_status)

        self.project_coordinator.map_scale_changed.connect(self._handle_map_scale_changed)

        self.project_coordinator.heightmap_path_changed.connect(self._handle_heightmap_path_changed)

        self.project_coordinator.autodrive_data_loaded.connect(self._handle_autodrive_data_loaded)

        self.edit_history.clean_changed.connect(self._handle_edit_clean_changed)

        self.edit_history.data_changed.connect(self._handle_data_changed)

        self.move_nodes_operation.status_changed.connect(self._set_status)

        self.delete_nodes_operation.status_changed.connect(self._set_status)

        self.connect_nodes_operation.status_changed.connect(self._set_status)

        self.create_nodes_operation.status_changed.connect(self._set_status)

        self.node_type_operation.status_changed.connect(self._set_status)

        self.rotate_selection_operation.status_changed.connect(self._set_status)

        # Keeps the tool buttons right even when the mode is changed
        # without clicking a button.
        self.view.interaction_mode_changed.connect(
            lambda interaction_mode: self.actions.sync_tool_actions()
        )

        self.node_selection.selection_changed.connect(
            lambda node_ids, primary_node_id: self.actions.delete_selection_action.setEnabled(
                bool(node_ids)
            )
        )

        self.view.rotation_step_changed.connect(self._handle_rotation_step_changed)

    def _handle_rotation_changed(self, rotation_angle: float):
        rotation_active = (
            abs(rotation_angle) >= ViewRotationController.ROTATION_COMPARISON_TOLERANCE
        )

        self.actions.reset_rotation_action.setEnabled(rotation_active)

        self.actions.rotation_controls.set_rotation_angle(rotation_angle)

    def _handle_rotation_step_changed(self, rotation_step: float):
        self.actions.rotation_controls.set_rotation_step(rotation_step)

    def _handle_heightmap_path_changed(self, file_path):
        self.actions.remove_heightmap_action.setEnabled(file_path is not None)

    def _handle_map_scale_changed(self, map_scale: int):
        self.actions.set_current_map_scale(map_scale)

    def _handle_autodrive_data_loaded(self, autodrive_data):
        # Edits of the previous data cannot be undone on new data.
        self.edit_history.clear()

        self.connect_nodes_operation.end_chain()

        self.setWindowModified(False)

    def _handle_data_changed(self, data_change: DataChange):
        self.scene_renderer.apply_changes(
            moved_node_ids=data_change.moved_node_ids,
            added_node_ids=data_change.added_node_ids,
            removed_node_ids=data_change.removed_node_ids,
            connection_node_ids=data_change.connection_node_ids,
            changed_flag_node_ids=data_change.changed_flag_node_ids,
        )

        if data_change.removed_node_ids:
            self.node_selection.remove(data_change.removed_node_ids)

        # Node coordinates in the info panel may have changed.
        self.selection_coordinator.refresh_info()

    def _handle_edit_clean_changed(self, clean: bool):
        self.setWindowModified(not clean)

    def _set_status(self, message: str):
        self.status.setText(message)
