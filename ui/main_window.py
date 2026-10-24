from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow,
    QFileDialog,
    QGraphicsScene,
    QWidget,
    QLabel,
    QHBoxLayout
)

from PySide6.QtGui import (
    QAction,
    QActionGroup
)

from PySide6.QtCore import Qt

from app_paths import (
    CONFIG_DIRECTORY,
    MARKER_ICON_PATH
)

from autodrive.xml_parser import AutoDriveXmlParser
from map.background_manager import BackgroundManager
from project.project_manager import ProjectManager
from rendering.scene_renderer import SceneRenderer
from ui.map_view import MapView

class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("AutoDrive FS25 Editor")
        self.resize(1400, 900)

        self.scene = QGraphicsScene()

        self.view = MapView()
        self.view.setScene(self.scene)
        self.autodrive_data = None

        self.background_manager = BackgroundManager(
            self.scene,
            map_scale=1
        )

        self.scene_renderer = SceneRenderer(
            self.scene,
            MARKER_ICON_PATH
        )

        self.config_directory = CONFIG_DIRECTORY

        self.project_manager = ProjectManager(
            self.config_directory
        )
        self.create_menu_bar()

        self.current_xml_path = None
        self.current_config_path = None
        self.current_heightmap_path = None

        self.status = QLabel(
            "Keine Datei geladen"
        )

        self.statusBar().addWidget(
            self.status,
            1
        )

        self.node_info = QLabel(
            "Keine Node ausgewählt"
        )

        self.node_info.setMinimumWidth(250)

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
            self.status.setText(
                f"DDS konnte nicht geladen werden: {ex}"
            )

            return

        self.scene.setSceneRect(
            self.scene.itemsBoundingRect()
        )

        if self.autodrive_data is None:
            self.view.fitInView(
                self.scene.sceneRect(),
                Qt.KeepAspectRatio
            )

        self.status.setText(
            "DDS-Hintergrund geladen"
        )

    def create_menu_bar(self):
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu(
            "Datei"
        )

        load_project_action = QAction(
            "Projekt laden",
            self
        )

        load_project_action.triggered.connect(
            self.load_project
        )

        file_menu.addAction(
            load_project_action
        )

        save_project_action = QAction(
            "Projekt speichern",
            self
        )

        save_project_action.triggered.connect(
            self.save_project
        )

        file_menu.addAction(
            save_project_action
        )

        file_menu.addSeparator()

        load_xml_action = QAction(
            "AutoDrive-XML laden",
            self
        )

        load_xml_action.triggered.connect(
            self.load_xml
        )

        file_menu.addAction(
            load_xml_action
        )

        file_menu.addSeparator()

        exit_action = QAction(
            "Beenden",
            self
        )

        exit_action.triggered.connect(
            self.close
        )

        file_menu.addAction(
            exit_action
        )

        map_menu = menu_bar.addMenu(
            "Karte"
        )

        select_dds_action = QAction(
            "DDS auswählen",
            self
        )

        select_dds_action.triggered.connect(
            self.select_background
        )

        map_menu.addAction(
            select_dds_action
        )

        map_menu.addSeparator()

        map_size_menu = map_menu.addMenu(
            "Kartengröße"
        )

        self.map_scale_action_group = QActionGroup(
            self
        )

        self.map_scale_action_group.setExclusive(
            True
        )

        self.map_scale_actions = {}

        map_sizes = (
            ("Originalgröße", 1),
            ("4x-Karte", 2),
            ("16x-Karte", 4),
            ("64x-Karte", 8)
        )

        for label, scale in map_sizes:
            action = QAction(
                label,
                self
            )

            action.setCheckable(
                True
            )

            action.setData(
                scale
            )

            action.triggered.connect(
                lambda checked, selected_scale=scale:
                self.set_map_scale(
                    selected_scale
                )
                if checked
                else None
            )

            self.map_scale_action_group.addAction(
                action
            )

            map_size_menu.addAction(
                action
            )

            self.map_scale_actions[scale] = action

        current_scale = (
            self.background_manager.map_scale
        )

        current_action = (
            self.map_scale_actions.get(
                current_scale
            )
        )

        if current_action is not None:
            current_action.setChecked(
                True
            )

    def set_map_scale(self, map_scale):
        try:
            self.background_manager.set_map_scale(
                map_scale
            )

        except Exception as ex:
            self.status.setText(
                f"Kartengröße konnte nicht geändert werden: {ex}"
            )

            return

        action = self.map_scale_actions.get(
            map_scale
        )

        if action is not None:
            action.setChecked(
                True
            )

        self.scene.setSceneRect(
            self.scene.itemsBoundingRect()
        )

        self.status.setText(
            f"Kartengröße: "
            f"{action.text() if action else map_scale}"
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
            self.load_xml_file(
                filename
            )

        except Exception as ex:
            self.status.setText(
                f"XML konnte nicht geladen werden: {ex}"
            )

    def load_xml_file(self, filename):
        xml_path = Path(
            filename
        ).resolve()

        autodrive_data = AutoDriveXmlParser.load(
            xml_path
        )

        self.background_manager.remove_from_scene(
            preserve_file_path=True
        )

        self.scene_renderer.reset()

        self.scene.clear()

        self.current_xml_path = str(
            xml_path
        )

        self.autodrive_data = autodrive_data

        self.background_manager.restore()

        self.scene_renderer.render(
            self.autodrive_data,
            self.show_node_info
        )

        self.scene.setSceneRect(
            self.scene.itemsBoundingRect()
        )

        self.view.fitInView(
            self.scene.sceneRect(),
            Qt.KeepAspectRatio
        )

        self.status.setText(
            f"{len(self.autodrive_data)} Waypoints geladen"
        )

    def save_project(self):
        if not self.current_xml_path:
            self.status.setText(
                "Bitte zuerst eine AutoDrive-XML laden"
            )
            return

        if self.current_config_path:
            default_path = self.current_config_path
        else:
            default_path = str(
                self.config_directory
            )

        config_path, _ = (
            QFileDialog.getSaveFileName(
                self,
                "Projektkonfiguration speichern",
                default_path,
                "JSON-Konfiguration (*.json)"
            )
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
            self.status.setText(
                f"Projekt konnte nicht gespeichert werden: {ex}"
            )
            return

        self.current_config_path = str(
            saved_path
        )

        self.status.setText(
            f"Projekt gespeichert: {saved_path.name}"
        )

    def load_project(self):
        config_path, _ = (
            QFileDialog.getOpenFileName(
                self,
                "Projektkonfiguration öffnen",
                str(self.config_directory),
                "JSON-Konfiguration (*.json)"
            )
        )

        if not config_path:
            return

        try:
            project_data = (
                self.project_manager.load_project(
                    config_path
                )
            )

            map_scale = project_data[
                "map_scale"
            ]

            if map_scale not in self.map_scale_actions:
                raise ValueError(
                    f"Unbekannte Kartengröße: {map_scale}"
                )

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

            self.current_heightmap_path = (
                project_data["heightmap"]
            )

            self.load_xml_file(
                project_data["autodrive_xml"]
            )

        except Exception as ex:
            self.status.setText(
                f"Projekt konnte nicht geladen werden: {ex}"
            )
            return

        self.current_config_path = config_path

        self.status.setText(
            f"Projekt geladen: {Path(config_path).name}"
        )

    def show_node_info(self, node_data):
        node_type = (
            "Regular Node"
            if node_data.is_regular
            else "Subprio Node"
        )

        marker_data = None

        if self.autodrive_data is not None:
            marker_data = (
                self.autodrive_data.get_marker(
                    node_data.node_id
                )
            )

        marker_text = ""

        if marker_data is not None:
            marker_text = (
                f"\n\n"
                f"Marker: {marker_data.name}\n\n"
                f"Gruppe: {marker_data.group}"
            )

        self.node_info.setText(
            f"""
    Node ID: {node_data.node_id}

    Typ: {node_type}
    {marker_text}

    X: {node_data.x:.2f}
    Y: {node_data.y:.2f}
    Z: {node_data.z:.2f}
    """
        )