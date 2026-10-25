from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QGraphicsScene,
    QLabel,
    QMainWindow
)

from app_paths import (
    LOCAL_PROJECTS_DIRECTORY,
    MARKER_ICON_PATH
)
from autodrive.models import (
    AutoDriveData,
    NodeData
)
from map.background_manager import BackgroundManager
from map.heightmap_manager import HeightmapManager
from project.project_manager import ProjectManager
from project.project_coordinator import (
    ProjectCoordinator
)
from rendering.scene_renderer import SceneRenderer
from rendering.display_style import DisplayStyle
from ui.display_options_dialog import (
    DisplayOptionsDialog
)
from ui.interaction_mode import InteractionMode
from ui.main_window_actions import MainWindowActions
from ui.map_tools.measure_tool import MeasureTool
from ui.map_tools.move_nodes_tool import MoveNodesTool
from ui.map_tools.select_tool import SelectTool
from ui.map_view import MapView
from ui.node_info_formatter import NodeInfoFormatter
from ui.view_rotation_controller import ViewRotationController
from ui.debug_dock import DebugDock
from ui.debug_dock_coordinator import DebugDockCoordinator
from ui.grid_coordinator import GridCoordinator
from editing.edit_command import DataChange
from editing.edit_coordinator import EditCoordinator
from editing.node_drag_coordinator import NodeDragCoordinator
from selection.node_selection_manager import (
    NodeSelectionManager
)
from selection.selection_coordinator import (
    SelectionCoordinator
)
from measurement.measurement_controller import (
    MeasurementController
)
from measurement.measurement_mode import (
    MeasurementMode
)
from measurement.measurement_coordinator import (
    MeasurementCoordinator
)

class MainWindow(QMainWindow):

    WINDOW_TITLE = "AutoDrive FS25 Editor"
    INITIAL_WIDTH = 1400
    INITIAL_HEIGHT = 900

    NO_FILE_STATUS = "Keine Datei geladen"
    NO_SELECTION_INFO = "Keine Node ausgewählt"

    DEFAULT_MAP_SCALE = 1

    def __init__(self):
        super().__init__()

        self.local_projects_directory = (
            LOCAL_PROJECTS_DIRECTORY
        )

        self._configure_window()
        self._create_scene_and_view()
        self._create_managers()
        self._create_status_widgets()
        self._create_central_widget()
        self._create_debug_dock()

        self.actions = MainWindowActions(
            self
        )

        self.actions.set_current_map_scale(
            self.background_manager.map_scale
        )

        self.grid_coordinator = GridCoordinator(
            background_manager=self.background_manager,
            grid_controls=self.actions.grid_controls,
            parent=self
        )

        self._connect_signals()

        # Created after the renderer is connected to the view, so the
        # dock reads the renderer state after it has been updated.
        self.debug_dock_coordinator = DebugDockCoordinator(
            debug_dock=self.debug_dock,
            view=self.view,
            scene_renderer=self.scene_renderer,
            parent=self
        )

        self.selection_coordinator.selection_state_changed.connect(
            self.debug_dock_coordinator.refresh
        )

        self.project_coordinator.debug_refresh_requested.connect(
            self.debug_dock_coordinator.refresh
        )

    def select_background(self):
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "overview.dds auswählen",
            "",
            "DDS-Bilder (*.dds);;Alle Dateien (*)"
        )

        if not filename:
            return

        try:
            self.project_coordinator.load_background_file(
                filename
            )

        except Exception as ex:
            self._set_status(
                f"DDS konnte nicht geladen werden: {ex}"
            )

    def select_heightmap(self):
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "dem.png auswählen",
            "",
            "PNG-Heightmaps (*.png);;Alle Dateien (*)"
        )

        if not filename:
            return

        try:
            self.project_coordinator.load_heightmap_file(
                filename
            )

        except Exception as ex:
            self._set_status(
                f"Heightmap konnte nicht geladen werden: {ex}"
            )

    def remove_heightmap(self):
        self.project_coordinator.remove_heightmap()

    def set_map_scale(
        self,
        map_scale: int
    ):
        action = self.actions.map_scale_actions.get(
            map_scale
        )

        map_scale_label = (
            action.text()
            if action is not None
            else str(map_scale)
        )

        try:
            self.project_coordinator.set_map_scale(
                map_scale=map_scale,
                map_scale_label=map_scale_label
            )

        except Exception as ex:
            self._set_status(
                "Kartengröße konnte nicht geändert werden: "
                f"{ex}"
            )

    def load_xml(self):
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "AutoDrive XML öffnen",
            "",
            "XML (*.xml)"
        )

        if not filename:
            return

        try:
            self.project_coordinator.load_xml_file(
                filename
            )

        except Exception as ex:
            self._set_status(
                f"XML konnte nicht geladen werden: {ex}"
            )

    def load_xml_file(
        self,
        filename
    ):
        self.project_coordinator.load_xml_file(
            filename
        )

    def save_project(self):
        if not self.project_coordinator.current_xml_path:
            self._set_status(
                "Bitte zuerst eine AutoDrive-XML laden"
            )
            return

        default_path = (
            self.project_coordinator.current_config_path
            if self.project_coordinator.current_config_path
            else str(
                self.local_projects_directory
            )
        )

        config_path, _ = QFileDialog.getSaveFileName(
            self,
            "Projektkonfiguration speichern",
            default_path,
            "JSON-Konfiguration (*.json)"
        )

        if not config_path:
            return

        if not config_path.lower().endswith(
            ".json"
        ):
            config_path += ".json"

        try:
            self.project_coordinator.save_project_file(
                config_path
            )

        except Exception as ex:
            self._set_status(
                f"Projekt konnte nicht gespeichert werden: "
                f"{ex}"
            )

    def load_project(self):
        config_path, _ = QFileDialog.getOpenFileName(
            self,
            "Projektkonfiguration öffnen",
            str(
                self.local_projects_directory
            ),
            "JSON-Konfiguration (*.json)"
        )

        if not config_path:
            return

        try:
            self.project_coordinator.load_project_file(
                config_path
            )

        except Exception as ex:
            self._set_status(
                f"Projekt konnte nicht geladen werden: "
                f"{ex}"
            )

    def show_node_info(
        self,
        node_data: NodeData
    ):
        self.selection_coordinator.show_node_info(
            node_data
        )

    def set_interaction_mode(
        self,
        interaction_mode: InteractionMode
    ):
        self.view.set_interaction_mode(
            interaction_mode
        )

        self._set_status(
            f"Modus: {interaction_mode.display_name}"
        )

    def set_view_rotation(
        self,
        rotation_angle: float
    ):
        self.view.set_rotation_angle(
            rotation_angle
        )

        self._set_status(
            f"Rotation: "
            f"{self.view.rotation_angle:.2f}°"
        )

    def set_view_rotation_step(
        self,
        rotation_step: float
    ):
        self.view.set_rotation_step(
            rotation_step
        )

        self._set_status(
            f"Rotationsraster: "
            f"{self.view.rotation_step:.2f}°"
        )

    def reset_view_rotation(self):
        self.view.reset_view_rotation()

        self._set_status(
            "Rotation zurückgesetzt"
        )

    def set_measurement_mode(
        self,
        measurement_mode: MeasurementMode
    ):
        self.measurement_coordinator.set_mode(
            measurement_mode
        )

    def align_view_to_measurement(self):
        self.measurement_coordinator.align_view_to_measurement()

    def open_display_options(self):
        dialog = DisplayOptionsDialog(
            display_style=(
                self.scene_renderer.display_style
            ),
            parent=self
        )

        dialog.style_applied.connect(
            self.apply_display_style
        )

        dialog.exec()

    def apply_display_style(
        self,
        display_style: DisplayStyle
    ):
        if not isinstance(
            display_style,
            DisplayStyle
        ):
            raise TypeError(
                "Der Darstellungsstil ist ungültig."
            )

        self.scene_renderer.set_display_style(
            display_style
        )

        self.project_coordinator.rebuild_scene_after_style_change()

    def _configure_window(self):
        # Qt shows "*" in place of "[*]" while the window is modified.
        self.setWindowTitle(
            f"{self.WINDOW_TITLE}[*]"
        )

        self.resize(
            self.INITIAL_WIDTH,
            self.INITIAL_HEIGHT
        )

    def _create_scene_and_view(self):
        self.scene = QGraphicsScene()

        self.view = MapView()

        self.view.setScene(
            self.scene
        )

    def _create_managers(self):
        self.background_manager = BackgroundManager(
            self.scene,
            map_scale=self.DEFAULT_MAP_SCALE
        )

        self.heightmap_manager = HeightmapManager()

        self.node_info_formatter = NodeInfoFormatter(
            background_manager=self.background_manager,
            heightmap_manager=self.heightmap_manager
        )

        self.scene_renderer = SceneRenderer(
            self.scene,
            MARKER_ICON_PATH
        )

        self.project_manager = ProjectManager(
            self.local_projects_directory
        )

        self.node_selection_manager = (
            NodeSelectionManager()
        )

        self.selection_coordinator = (
            SelectionCoordinator(
                view=self.view,
                renderer=self.scene_renderer,
                selection_manager=(
                    self.node_selection_manager
                ),
                node_info_formatter=(
                    self.node_info_formatter
                ),
                autodrive_data_provider=(
                    self._get_autodrive_data
                ),
                parent=self
            )
        )

        self.measurement_controller = (
            MeasurementController(
                scene=self.scene,
                parent=self
            )
        )

        self.measurement_coordinator = (
            MeasurementCoordinator(
                view=self.view,
                controller=(
                    self.measurement_controller
                ),
                node_item_provider=(
                    self.selection_coordinator
                    .get_node_item_at
                ),
                parent=self
            )
        )

        self.edit_coordinator = EditCoordinator(
            parent=self
        )

        self.node_drag_coordinator = NodeDragCoordinator(
            view=self.view,
            selection_coordinator=self.selection_coordinator,
            selection_manager=self.node_selection_manager,
            edit_coordinator=self.edit_coordinator,
            autodrive_data_provider=self._get_autodrive_data,
            parent=self
        )

        self._register_map_tools()

        self.project_coordinator = (
            ProjectCoordinator(
                scene=self.scene,
                view=self.view,
                project_manager=(
                    self.project_manager
                ),
                background_manager=(
                    self.background_manager
                ),
                heightmap_manager=(
                    self.heightmap_manager
                ),
                scene_renderer=(
                    self.scene_renderer
                ),
                selection_coordinator=(
                    self.selection_coordinator
                ),
                measurement_coordinator=(
                    self.measurement_coordinator
                ),
                parent=self
            )
        )

    def _register_map_tools(self):
        self.view.register_tool(
            InteractionMode.SELECT,
            SelectTool(
                self.view,
                self.selection_coordinator
            )
        )

        self.view.register_tool(
            InteractionMode.MOVE_NODES,
            MoveNodesTool(
                self.view,
                self.node_drag_coordinator
            )
        )

        self.view.register_measure_tool(
            MeasureTool(
                self.view,
                self.measurement_coordinator
            )
        )

    def _get_autodrive_data(
        self
    ) -> AutoDriveData | None:
        return (
            self.project_coordinator
            .autodrive_data
        )

    def _create_status_widgets(self):
        self.status = QLabel(
            self.NO_FILE_STATUS
        )

        self.statusBar().addWidget(
            self.status,
            1
        )

    def _create_central_widget(self):
        self.setCentralWidget(
            self.view
        )

    def _create_debug_dock(self):
        self.debug_dock = DebugDock(
            self
        )

        self.addDockWidget(
            Qt.RightDockWidgetArea,
            self.debug_dock
        )

        self.debug_dock.set_node_info(
            self.NO_SELECTION_INFO
        )

        self.debug_dock.hide()

    def _connect_signals(self):
        self.view.zoom_changed.connect(
            self.scene_renderer.update_visibility_for_zoom
        )

        self.view.visible_scene_rect_changed.connect(
            self.scene_renderer.update_visible_scene_rect
        )

        self.view.rotation_changed.connect(
            self._handle_rotation_changed
        )

        self.measurement_coordinator.status_changed.connect(
            self._set_status
        )

        self.measurement_coordinator.measurement_mode_changed.connect(
            self.actions.set_measurement_mode
        )

        self.measurement_coordinator.alignment_available_changed.connect(
            self.actions.set_measurement_alignment_enabled
        )

        self.selection_coordinator.selection_info_changed.connect(
            self.debug_dock.set_node_info
        )

        self.project_coordinator.status_changed.connect(
            self._set_status
        )

        self.grid_coordinator.status_changed.connect(
            self._set_status
        )

        self.project_coordinator.map_scale_changed.connect(
            self._handle_map_scale_changed
        )

        self.project_coordinator.heightmap_path_changed.connect(
            self._handle_heightmap_path_changed
        )

        self.project_coordinator.autodrive_data_loaded.connect(
            self._handle_autodrive_data_loaded
        )

        self.edit_coordinator.clean_changed.connect(
            self._handle_edit_clean_changed
        )

        self.edit_coordinator.data_changed.connect(
            self._handle_data_changed
        )

        self.node_drag_coordinator.status_changed.connect(
            self._set_status
        )

        self.view.rotation_step_changed.connect(
            self._handle_rotation_step_changed
        )

    def _handle_rotation_changed(
        self,
        rotation_angle: float
    ):
        rotation_active = (
            abs(rotation_angle)
            >= ViewRotationController.ROTATION_COMPARISON_TOLERANCE
        )

        self.actions.reset_rotation_action.setEnabled(
            rotation_active
        )

        self.actions.rotation_controls.set_rotation_angle(
            rotation_angle
        )

    def _handle_rotation_step_changed(
        self,
        rotation_step: float
    ):
        self.actions.rotation_controls.set_rotation_step(
            rotation_step
        )

    def _handle_heightmap_path_changed(
        self,
        file_path
    ):
        self.actions.remove_heightmap_action.setEnabled(
            file_path is not None
        )

    def _handle_map_scale_changed(
        self,
        map_scale: int
    ):
        self.actions.set_current_map_scale(
            map_scale
        )

    def _handle_autodrive_data_loaded(
        self,
        autodrive_data
    ):
        # Edits of the previous data cannot be undone on new data.
        self.edit_coordinator.clear()

        self.setWindowModified(
            False
        )

    def _handle_data_changed(
        self,
        data_change: DataChange
    ):
        self.scene_renderer.update_node_positions(
            data_change.changed_node_ids
        )

        # Node coordinates in the info panel may have changed.
        self.selection_coordinator.refresh_info()

    def _handle_edit_clean_changed(
        self,
        clean: bool
    ):
        self.setWindowModified(
            not clean
        )

    def _set_status(
        self,
        message: str
    ):
        self.status.setText(
            message
        )
