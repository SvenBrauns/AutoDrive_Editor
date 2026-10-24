from pathlib import Path

from PySide6.QtCore import (
    QPoint,
    Qt
)
from PySide6.QtWidgets import (
    QFileDialog,
    QGraphicsScene,
    QLabel,
    QMainWindow
)
from PySide6.QtGui import QPainterPath

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
from rendering.items.node_item import NodeItem
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

        self._refresh_selected_node_info()

    def remove_heightmap(self):
        self.heightmap_manager.clear()

        self._set_heightmap_path(
            None
        )

        self._set_status(
            "Heightmap entfernt"
        )

        self._refresh_selected_node_info()

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

        self._refresh_selected_node_info()

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

        self._clear_node_selection()

        self.background_manager.restore()

        self.scene_renderer.render(
            self.autodrive_data
        )

        self.scene_renderer.set_selected_node_ids(
            self.node_selection_manager.selected_node_ids
        )

        self._update_scene_rect()
        self._fit_scene_in_view()

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
        self.node_selection_manager.replace(
            {node_data.node_id},
            primary_node_id=node_data.node_id
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

    def reset_view_rotation(self):
        self.view.reset_view_rotation()

        self._set_status(
            "Rotation zurückgesetzt"
        )

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

        selected_node_ids = (
            self.node_selection_manager.selected_node_ids
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

        self.scene_renderer.set_selected_node_ids(
            selected_node_ids
        )

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

    def handle_selection_click(
        self,
        view_position: QPoint,
        modifiers
    ):
        clicked_node = None

        for item in self.view.items(
            view_position
        ):
            if isinstance(
                item,
                NodeItem
            ):
                clicked_node = item.node_data
                break

        control_pressed = bool(
            modifiers
            & Qt.ControlModifier
        )

        if clicked_node is None:
            if not control_pressed:
                self.node_selection_manager.clear()

            return

        if control_pressed:
            self.node_selection_manager.toggle(
                clicked_node.node_id
            )

        else:
            self.node_selection_manager.replace(
                {clicked_node.node_id},
                primary_node_id=clicked_node.node_id
            )

    def handle_selection_area(
        self,
        selection_path: QPainterPath,
        modifiers
    ):
        selected_nodes = (
            self.scene_renderer.get_nodes_in_selection_path(
                selection_path
            )
        )

        selected_node_ids = {
            node_data.node_id
            for node_data in selected_nodes
        }

        primary_node_id = (
            min(selected_node_ids)
            if selected_node_ids
            else None
        )

        control_pressed = bool(
            modifiers
            & Qt.ControlModifier
        )

        if control_pressed:
            self.node_selection_manager.toggle_many(
                selected_node_ids,
                primary_node_id=primary_node_id
            )

        else:
            self.node_selection_manager.replace(
                selected_node_ids,
                primary_node_id=primary_node_id
            )

    def handle_selection_area_preview(
        self,
        selection_path: QPainterPath,
        modifiers
    ):
        preview_nodes = (
            self.scene_renderer.get_nodes_in_selection_path(
                selection_path
            )
        )

        area_node_ids = {
            node_data.node_id
            for node_data in preview_nodes
        }

        current_node_ids = (
            self.node_selection_manager.selected_node_ids
        )

        control_pressed = bool(
            modifiers
            & Qt.ControlModifier
        )

        if control_pressed:
            preview_node_ids = (
                current_node_ids
                ^ area_node_ids
            )

        else:
            preview_node_ids = area_node_ids

        self.scene_renderer.set_selected_node_ids(
            preview_node_ids
        )

    def clear_selection_area_preview(self):
        self.scene_renderer.set_selected_node_ids(
            self.node_selection_manager.selected_node_ids
        )

    def _format_selection_info(
        self,
        selected_node_ids,
        primary_node_id
    ) -> str:
        if not selected_node_ids:
            return self.NO_SELECTION_INFO

        selection_count = len(
            selected_node_ids
        )

        if (
            self.autodrive_data is None
            or primary_node_id is None
        ):
            return (
                f"{selection_count} Nodes ausgewählt"
            )

        primary_node = self.autodrive_data.get_node(
            primary_node_id
        )

        if primary_node is None:
            return (
                f"{selection_count} Nodes ausgewählt"
            )

        node_info_text = (
            self.node_info_formatter.format_node_info(
                node_data=primary_node,
                autodrive_data=self.autodrive_data
            )
        )

        if selection_count == 1:
            return node_info_text

        return (
            f"{selection_count} Nodes ausgewählt\n"
            f"Primäre Auswahl: {primary_node_id}\n\n"
            f"{node_info_text}"
        )

    def _handle_node_selection_changed(
        self,
        selected_node_ids,
        primary_node_id
    ):
        self.scene_renderer.set_selected_node_ids(
            selected_node_ids
        )

        selection_info = self._format_selection_info(
            selected_node_ids,
            primary_node_id
        )

        self.debug_dock.set_node_info(
            selection_info
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
            self.handle_selection_click
        )

        self.view.rotation_changed.connect(
            self._handle_rotation_changed
        )

        self.view.selection_area_requested.connect(
            self.handle_selection_area
        )

        self.view.selection_area_preview_requested.connect(
            self.handle_selection_area_preview
        )

        self.view.selection_area_preview_cleared.connect(
            self.clear_selection_area_preview
        )

        self.node_selection_manager.selection_changed.connect(
            self._handle_node_selection_changed
        )

        self.view.zoom_changed.connect(
            self._refresh_debug_dock
        )

        self.view.rotation_changed.connect(
            self._refresh_debug_dock
        )

        self.view.visible_scene_rect_changed.connect(
            self._refresh_debug_dock
        )

        self.view.interaction_mode_changed.connect(
            self._refresh_debug_dock
        )

        self.node_selection_manager.selection_changed.connect(
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

        self._clear_node_selection()

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
        self.background_manager.remove_from_scene(
            preserve_file_path=True
        )

        self.scene_renderer.reset()
        self.scene.clear()

    def _clear_node_selection(self):
        self.node_selection_manager.clear()

    def _refresh_selected_node_info(self):
        selection_info = self._format_selection_info(
            self.node_selection_manager.selected_node_ids,
            self.node_selection_manager.primary_node_id
        )

        self.debug_dock.set_node_info(
            selection_info
        )

    def _update_scene_rect(self):
        self.scene.setSceneRect(
            self.scene.itemsBoundingRect()
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