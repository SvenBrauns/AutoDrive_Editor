from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow,
    QFileDialog,
    QGraphicsScene,
    QGraphicsLineItem,
    QWidget,
    QLabel,
    QHBoxLayout
)

from PySide6.QtGui import (
    QAction,
    QActionGroup,
    QColor,
    QPen
)

from PySide6.QtCore import Qt

from ui.map_view import MapView
from project.project_manager import ProjectManager
from map.background_manager import BackgroundManager
from app_paths import (
    CONFIG_DIRECTORY,
    MARKER_ICON_PATH
)
from items.node_item import NodeItem
from items.marker_item import MarkerItem

from autodrive.xml_parser import AutoDriveXmlParser

class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("AutoDrive FS25 Editor")
        self.resize(1400, 900)

        self.scene = QGraphicsScene()

        self.view = MapView()
        self.view.setScene(self.scene)
        self.waypoints = []
        self.marker_data = {}
        self.autodrive_data = None

        self.background_manager = BackgroundManager(
            self.scene,
            map_scale=1
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

        if not self.waypoints:
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

        self.scene.clear()

        self.waypoints.clear()
        self.marker_data.clear()

        self.current_xml_path = str(
            xml_path
        )

        self.autodrive_data = autodrive_data

        self.background_manager.restore()

        sorted_nodes = (
            self.autodrive_data.get_sorted_nodes()
        )

        for node_data in sorted_nodes:
            item = NodeItem(
                node_data.node_id,
                node_data.x,
                node_data.y,
                node_data.z,
                node_data.flag,
                self
            )

            self.scene.addItem(
                item
            )

            self.waypoints.append(
                item
            )

        for marker_data in (
            self.autodrive_data.markers.values()
        ):
            self.marker_data[marker_data.node_id] = {
                "name": marker_data.name,
                "group": marker_data.group
            }

            node_item = self._get_waypoint_item(
                marker_data.node_id
            )

            if node_item is None:
                continue

            marker_item = MarkerItem(
                str(MARKER_ICON_PATH)
            )

            marker_item.setScale(
                0.15
            )

            marker_item.setPos(
                node_item.pos().x() - 5,
                node_item.pos().y() - 12
            )

            self.scene.addItem(
                marker_item
            )

        self._create_connections()

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

    def _get_waypoint_item(self, node_id):
        waypoint_index = node_id - 1

        if waypoint_index < 0:
            return None

        if waypoint_index >= len(self.waypoints):
            return None

        waypoint_item = self.waypoints[
            waypoint_index
        ]

        if waypoint_item.index != node_id:
            return None

        return waypoint_item

    def _create_connections(self):
        regular_pen = QPen(
            QColor(0, 255, 0)
        )

        dual_pen = QPen(
            QColor(0, 0, 255)
        )

        reverse_pen = QPen(
            QColor(100, 220, 255)
        )

        for source_node in (
            self.autodrive_data.get_sorted_nodes()
        ):
            source_item = self._get_waypoint_item(
                source_node.node_id
            )

            if source_item is None:
                continue

            for target_id in source_node.outgoing:
                target_node = (
                    self.autodrive_data.get_node(
                        target_id
                    )
                )

                target_item = self._get_waypoint_item(
                    target_id
                )

                if target_node is None:
                    continue

                if target_item is None:
                    continue

                is_dual = (
                    target_id in source_node.outgoing
                    and target_id in source_node.incoming
                    and source_node.node_id in target_node.outgoing
                    and source_node.node_id in target_node.incoming
                )

                is_reverse = (
                    target_id in source_node.outgoing
                    and source_node.node_id
                    not in target_node.incoming
                )

                line = QGraphicsLineItem(
                    source_item.pos().x(),
                    source_item.pos().y(),
                    target_item.pos().x(),
                    target_item.pos().y()
                )

                if is_dual:
                    line.setPen(
                        dual_pen
                    )

                elif is_reverse:
                    line.setPen(
                        reverse_pen
                    )

                else:
                    line.setPen(
                        regular_pen
                    )

                self.scene.addItem(
                    line
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

    def show_node_info(self, node):
    
        node_type = (
            "Regular Node"
            if node.flag == 0
            else "Subprio Node"
        )

        marker_text = ""

        if node.index in self.marker_data:

            marker = self.marker_data[node.index]

            marker_text = f"""

            Marker: {marker['name']}

            Gruppe: {marker['group']}
            """

        self.node_info.setText(
            f"""
            Node ID: {node.index}

            Typ: {node_type}
            {marker_text}
            X: {node.x_coord:.2f}
            Y: {node.y_coord:.2f}
            Z: {node.z_coord:.2f}
            """
        )