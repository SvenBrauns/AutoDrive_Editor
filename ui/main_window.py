from pathlib import Path

from PySide6.QtCore import (
    QPoint,
    Qt
)
from PySide6.QtWidgets import (
    QFileDialog,
    QGraphicsScene,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QWidget
)

from app_paths import (
    CONFIG_DIRECTORY,
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
from ui.interaction_mode import InteractionMode
from ui.main_window_actions import MainWindowActions
from ui.map_view import MapView
from ui.node_info_formatter import NodeInfoFormatter


class MainWindow(QMainWindow):

    WINDOW_TITLE = "AutoDrive FS25 Editor"
    INITIAL_WIDTH = 1400
    INITIAL_HEIGHT = 900

    NO_FILE_STATUS = "Keine Datei geladen"
    NO_NODE_INFO = "Keine Node ausgewählt"

    DEFAULT_MAP_SCALE = 1

    def __init__(self):
        super().__init__()

        self.autodrive_data: AutoDriveData | None = None
        self.selected_node_data: NodeData | None = None

        self.current_xml_path: str | None = None
        self.current_config_path: str | None = None
        self.current_heightmap_path: str | None = None

        self.config_directory = CONFIG_DIRECTORY

        self._configure_window()
        self._create_scene_and_view()
        self._create_managers()
        self._create_status_widgets()
        self._create_central_widget()

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

        self._update_scene_rect()
        self._fit_scene_in_view()

        self._set_status(
            f"{len(self.autodrive_data)} Waypoints geladen"
        )

    def save_project(self):
        if not self.current_xml_path:
            self._set_status(
                "Bitte zuerst eine AutoDrive-XML laden"
            )
            return

        default_path = (
            self.current_config_path
            if self.current_config_path
            else str(self.config_directory)
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
            str(self.config_directory),
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
        self.selected_node_data = node_data

        self.scene_renderer.select_node(
            node_data
        )

        node_info_text = (
            self.node_info_formatter.format_node_info(
                node_data=node_data,
                autodrive_data=self.autodrive_data
            )
        )

        self.node_info.setText(
            node_info_text
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

    def handle_selection_click(
        self,
        view_position: QPoint,
        modifiers
    ):
        for item in self.view.items(
            view_position
        ):
            if isinstance(
                item,
                NodeItem
            ):
                self.show_node_info(
                    item.node_data
                )
                return

        self._clear_node_selection()

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
            self.config_directory
        )

    def _create_status_widgets(self):
        self.status = QLabel(
            self.NO_FILE_STATUS
        )

        self.statusBar().addWidget(
            self.status,
            1
        )

        self.node_info = QLabel(
            self.NO_NODE_INFO
        )

        self.node_info.setMinimumWidth(
            250
        )

    def _create_central_widget(self):
        main_layout = QHBoxLayout()

        main_layout.addWidget(
            self.view,
            1
        )

        main_layout.addWidget(
            self.node_info
        )

        container = QWidget()

        container.setLayout(
            main_layout
        )

        self.setCentralWidget(
            container
        )

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
        self.selected_node_data = None

        self.scene_renderer.clear_selection()

        self.node_info.setText(
            self.NO_NODE_INFO
        )

    def _refresh_selected_node_info(self):
        if self.selected_node_data is None:
            return

        self.show_node_info(
            self.selected_node_data
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