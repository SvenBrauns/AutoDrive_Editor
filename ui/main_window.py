from pathlib import Path

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
from autodrive.xml_parser import AutoDriveXmlParser
from map.background_manager import BackgroundManager
from map.heightmap_manager import HeightmapManager
from project.project_manager import ProjectManager
from rendering.scene_renderer import SceneRenderer
from rendering.display_style import DisplayStyle
from ui.display_options_dialog import (
    DisplayOptionsDialog
)
from ui.interaction_mode import InteractionMode
from ui.main_window_actions import MainWindowActions
from ui.map_view import MapView
from ui.node_info_formatter import NodeInfoFormatter
from ui.debug_dock import DebugDock
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

        self.autodrive_data: AutoDriveData | None = None

        self.current_xml_path: str | None = None
        self.current_config_path: str | None = None
        self.current_heightmap_path: str | None = None

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

        self._connect_signals()

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
            self.background_manager.load(
                filename
            )

        except Exception as ex:
            self._set_status(
                f"DDS konnte nicht geladen werden: {ex}"
            )
            return

        self._update_scene_rect()

        if self.autodrive_data is None:
            self._fit_scene_in_view()

        self._set_status(
            "DDS-Hintergrund geladen"
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
            heightmap_data = (
                self.heightmap_manager.load(
                    filename
                )
            )

        except Exception as ex:
            self._set_status(
                f"Heightmap konnte nicht geladen werden: {ex}"
            )
            return

        self._set_heightmap_path(
            heightmap_data.file_path
        )

        self._set_status(
            f"Heightmap geladen: "
            f"{heightmap_data.width} × "
            f"{heightmap_data.height}, "
            f"{heightmap_data.format_description}"
        )

        self.selection_coordinator.refresh_info()

    def remove_heightmap(self):
        self.heightmap_manager.clear()

        self._set_heightmap_path(
            None
        )

        self._set_status(
            "Heightmap entfernt"
        )

        self.selection_coordinator.refresh_info()

    def set_map_scale(
        self,
        map_scale: int
    ):
        try:
            self.background_manager.set_map_scale(
                map_scale
            )

        except Exception as ex:
            self._set_status(
                "Kartengröße konnte nicht geändert werden: "
                f"{ex}"
            )
            return

        self.actions.set_current_map_scale(
            map_scale
        )

        self._update_scene_rect()

        action = self.actions.map_scale_actions.get(
            map_scale
        )

        map_scale_label = (
            action.text()
            if action is not None
            else str(map_scale)
        )

        self._set_status(
            f"Kartengröße: {map_scale_label}"
        )

        self.selection_coordinator.refresh_info()

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
            self.load_xml_file(
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
        xml_path = Path(
            filename
        ).resolve()

        autodrive_data = AutoDriveXmlParser.load(
            xml_path
        )

        self._clear_scene_content()

        self.current_xml_path = str(
            xml_path
        )

        self.autodrive_data = autodrive_data

        self.selection_coordinator.clear()

        self.background_manager.restore()

        self.scene_renderer.render(
            self.autodrive_data
        )

        self.selection_coordinator.synchronize()

        self._update_scene_rect()
        self._fit_scene_in_view()

        self.measurement_coordinator.restore_scene_items()

        self._set_status(
            f"{len(self.autodrive_data)} Waypoints geladen"
        )

        self._refresh_debug_dock()

    def save_project(self):
        if not self.current_xml_path:
            self._set_status(
                "Bitte zuerst eine AutoDrive-XML laden"
            )
            return

        default_path = (
            self.current_config_path
            if self.current_config_path
            else str(self.local_projects_directory)
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
            saved_path = (
                self.project_manager.save_project(
                    config_path=config_path,
                    xml_path=self.current_xml_path,
                    background_path=(
                        self.background_manager.file_path
                    ),
                    map_scale=(
                        self.background_manager.map_scale
                    ),
                    heightmap_path=(
                        self.current_heightmap_path
                    )
                )
            )

        except Exception as ex:
            self._set_status(
                f"Projekt konnte nicht gespeichert werden: {ex}"
            )
            return

        self.current_config_path = str(
            saved_path
        )

        self._set_status(
            f"Projekt gespeichert: {saved_path.name}"
        )

    def load_project(self):
        config_path, _ = QFileDialog.getOpenFileName(
            self,
            "Projektkonfiguration öffnen",
            str(self.local_projects_directory),
            "JSON-Konfiguration (*.json)"
        )

        if not config_path:
            return

        try:
            project_data = (
                self.project_manager.load_project(
                    config_path
                )
            )

            self._apply_project_data(
                project_data
            )

        except Exception as ex:
            self._set_status(
                f"Projekt konnte nicht geladen werden: {ex}"
            )
            return

        self.current_config_path = config_path

        project_name = Path(
            config_path
        ).name

        status_text = (
            f"Projekt geladen: {project_name}"
        )

        if self.heightmap_manager.has_heightmap():
            status_text += " mit Heightmap"

        self._set_status(
            status_text
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

        if interaction_mode == InteractionMode.NAVIGATE:
            self._set_status(
                "Modus: Navigation"
            )

        elif interaction_mode == InteractionMode.SELECT:
            self._set_status(
                "Modus: Auswahl"
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

        viewport_center = (
            self.view.viewport()
            .rect()
            .center()
        )

        scene_center = self.view.mapToScene(
            viewport_center
        )

        self.scene_renderer.set_display_style(
            display_style
        )

        if self.autodrive_data is None:
            self._set_status(
                "Darstellungsoptionen übernommen"
            )

            self._refresh_debug_dock()
            return

        self._clear_scene_content()

        self.background_manager.restore()

        self.scene_renderer.render(
            self.autodrive_data
        )

        self.selection_coordinator.synchronize()
        self.measurement_coordinator.restore_scene_items()

        self._update_scene_rect()

        self.view.centerOn(
            scene_center
        )

        self.scene_renderer.update_visibility_for_zoom(
            self.view.zoom_level
        )

        self.scene_renderer.update_visible_scene_rect(
            self.view.get_visible_scene_rect()
        )

        self._set_status(
            "Darstellungsoptionen übernommen"
        )

        self._refresh_debug_dock()

    def _configure_window(self):
        self.setWindowTitle(
            self.WINDOW_TITLE
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

    def _get_autodrive_data(
        self
    ) -> AutoDriveData | None:
        return self.autodrive_data

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

        self.view.selection_click_requested.connect(
            self.selection_coordinator.handle_click
        )

        self.view.rotation_changed.connect(
            self._handle_rotation_changed
        )

        self.view.selection_area_requested.connect(
            self.selection_coordinator.handle_area
        )

        self.view.selection_area_preview_requested.connect(
            self.selection_coordinator.handle_area_preview
        )

        self.view.selection_area_preview_cleared.connect(
            self.selection_coordinator.clear_area_preview
        )

        self.view.measurement_press_requested.connect(
            self.measurement_coordinator.handle_press
        )

        self.view.measurement_move_requested.connect(
            self.measurement_coordinator.handle_move
        )

        self.view.measurement_release_requested.connect(
            self.measurement_coordinator.handle_release
        )

        self.view.measurement_cancel_requested.connect(
            self.measurement_coordinator.cancel
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

        self.selection_coordinator.selection_state_changed.connect(
            self._refresh_debug_dock
        )

        self.view.zoom_changed.connect(
            self._refresh_debug_dock
        )

        self.view.rotation_changed.connect(
            self._refresh_debug_dock
        )

        self.view.rotation_step_changed.connect(
            self._handle_rotation_step_changed
        )

        self.view.visible_scene_rect_changed.connect(
            self._refresh_debug_dock
        )

        self.view.interaction_mode_changed.connect(
            self._refresh_debug_dock
        )

        self.debug_dock.visibilityChanged.connect(
            self._handle_debug_dock_visibility_changed
        )

    def _handle_rotation_changed(
        self,
        rotation_angle: float
    ):
        rotation_active = (
            abs(rotation_angle)
            >= self.view.ROTATION_COMPARISON_TOLERANCE
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

    def _refresh_debug_dock(
        self,
        *args
    ):
        if not self.debug_dock.isVisible():
            return

        self.debug_dock.set_interaction_mode(
            self.view.interaction_mode
        )

        self.debug_dock.set_view_state(
            zoom_level=self.view.zoom_level,
            rotation_angle=self.view.rotation_angle,
            visible_rect=(
                self.scene_renderer.current_visible_rect
            )
        )

        self.debug_dock.set_renderer_state(
            self.scene_renderer.get_debug_state()
        )

    def _handle_debug_dock_visibility_changed(
        self,
        visible: bool
    ):
        if visible:
            self._refresh_debug_dock()

    def _apply_project_data(
        self,
        project_data: dict
    ):
        map_scale = project_data[
            "map_scale"
        ]

        if map_scale not in self.actions.map_scale_actions:
            raise ValueError(
                f"Unbekannte Kartengröße: {map_scale}"
            )

        self.selection_coordinator.clear()

        self.set_map_scale(
            map_scale
        )

        background_path = project_data[
            "background_dds"
        ]

        if background_path:
            self.background_manager.load(
                background_path
            )

        else:
            self.background_manager.remove_from_scene(
                preserve_file_path=False
            )

        heightmap_path = project_data[
            "heightmap"
        ]

        if heightmap_path:
            heightmap_data = (
                self.heightmap_manager.load(
                    heightmap_path
                )
            )

            self._set_heightmap_path(
                heightmap_data.file_path
            )

        else:
            self.heightmap_manager.clear()

            self._set_heightmap_path(
                None
            )

        self.load_xml_file(
            project_data["autodrive_xml"]
        )

    def _set_heightmap_path(
        self,
        file_path
    ):
        self.current_heightmap_path = (
            str(file_path)
            if file_path is not None
            else None
        )

        self.actions.remove_heightmap_action.setEnabled(
            file_path is not None
        )

    def _clear_scene_content(self):
        self.measurement_coordinator.remove_scene_items()

        self.background_manager.remove_from_scene(
            preserve_file_path=True
        )

        self.scene_renderer.reset()
        self.scene.clear()

    def _update_scene_rect(self):
        scene_rect = (
            self.scene.itemsBoundingRect()
        )

        self.scene.setSceneRect(
            scene_rect
        )

        self.scene_renderer.update_scene_rect(
            scene_rect
        )

    def _fit_scene_in_view(self):
        scene_rect = self.scene.sceneRect()

        if scene_rect.isEmpty():
            return

        self.view.fitInView(
            scene_rect,
            Qt.KeepAspectRatio
        )

    def _set_status(
        self,
        message: str
    ):
        self.status.setText(
            message
        )

    def set_grid_visible(
        self,
        visible: bool
    ):
        self.background_manager.set_grid_visible(
            visible
        )

        self.actions.grid_controls.set_grid_visible(
            self.background_manager.grid_visible
        )

        if self.background_manager.grid_visible:
            status_text = "Raster eingeblendet"

        else:
            status_text = "Raster ausgeblendet"

        self._set_status(
            status_text
        )

    def set_measurement_mode(
        self,
        measurement_mode: MeasurementMode
    ):
        self.measurement_coordinator.set_mode(
            measurement_mode
        )

    def set_grid_spacing(
        self,
        spacing: float
    ):
        try:
            self.background_manager.set_grid_spacing(
                spacing
            )

        except Exception as ex:
            self._set_status(
                f"Rasterabstand konnte nicht "
                f"geändert werden: {ex}"
            )
            return

        self.actions.grid_controls.set_grid_spacing(
            self.background_manager.grid_spacing
        )

        self._set_status(
            f"Rasterabstand: "
            f"{self.background_manager.grid_spacing:.2f} m"
        )

    def set_grid_rotation(
        self,
        rotation_angle: float
    ):
        self.background_manager.set_grid_rotation(
            rotation_angle
        )

        self.actions.grid_controls.set_grid_rotation(
            self.background_manager.grid_rotation
        )

        self._set_status(
            f"Rasterrotation: "
            f"{self.background_manager.grid_rotation:.2f}°"
        )

    def reset_grid(self):
        self.background_manager.reset_grid()

        self.actions.grid_controls.set_grid_visible(
            self.background_manager.grid_visible
        )

        self.actions.grid_controls.set_grid_spacing(
            self.background_manager.grid_spacing
        )

        self.actions.grid_controls.set_grid_rotation(
            self.background_manager.grid_rotation
        )

        self._set_status(
            "Raster zurückgesetzt"
        )