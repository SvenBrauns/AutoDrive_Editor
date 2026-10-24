import xml.etree.ElementTree as ET

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
from pathlib import Path
from ui.map_view import MapView
from project.project_manager import ProjectManager
from map.background_manager import BackgroundManager

from items.node_item import NodeItem
from items.marker_item import MarkerItem

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

        self.background_manager = BackgroundManager(
            self.scene,
            map_scale=1
        )

        project_root = Path(
            __file__
        ).resolve().parent.parent

        self.config_directory = (
            project_root / "config"
        )

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
        self.current_xml_path = str(
            Path(filename).resolve()
        )

        self.background_manager.remove_from_scene(
            preserve_file_path=True
        )

        self.scene.clear()

        self.waypoints.clear()
        self.marker_data.clear()

        tree = ET.parse(
            self.current_xml_path
        )

        root = tree.getroot()

        waypoint_section = root.find(
            "waypoints"
        )

        if waypoint_section is None:
            raise ValueError(
                "Die XML enthält keinen Waypoint-Bereich."
            )

        markers_section = root.find(
            "markers"
        )

        x_node = waypoint_section.find("x")
        y_node = waypoint_section.find("y")
        z_node = waypoint_section.find("z")

        if (
            x_node is None
            or y_node is None
            or z_node is None
        ):
            raise ValueError(
                "x/y/z-Daten fehlen."
            )

        xs = [
            float(value)
            for value in x_node.text.split(";")
            if value
        ]

        ys = [
            float(value)
            for value in y_node.text.split(";")
            if value
        ]

        zs = [
            float(value)
            for value in z_node.text.split(";")
            if value
        ]

        self.background_manager.restore()

        out_node = waypoint_section.find(
            "out"
        )

        if out_node is not None and out_node.text:
            out_connections = out_node.text.split(";")
        else:
            out_connections = []

        in_node = waypoint_section.find(
            "in"
        )

        if in_node is not None and in_node.text:
            in_connections = in_node.text.split(";")
        else:
            in_connections = []

        flags_node = waypoint_section.find(
            "flags"
        )

        if flags_node is not None and flags_node.text:
            flag_values = flags_node.text.split(";")
        else:
            flag_values = ["0"] * len(xs)

        count = min(
            len(xs),
            len(ys),
            len(zs),
            len(flag_values)
        )

        for index in range(count):
            item = NodeItem(
                index + 1,
                xs[index],
                ys[index],
                zs[index],
                int(flag_values[index]),
                self
            )

            self.scene.addItem(
                item
            )

            self.waypoints.append(
                item
            )

        if markers_section is not None:
            for marker in markers_section:
                try:
                    node_id = int(
                        marker.attrib["i"]
                    )

                    marker_name = marker.attrib.get(
                        "n",
                        ""
                    )

                    marker_group = marker.attrib.get(
                        "g",
                        ""
                    )

                    self.marker_data[node_id] = {
                        "name": marker_name,
                        "group": marker_group
                    }

                    if node_id <= 0:
                        continue

                    if node_id > len(self.waypoints):
                        continue

                    node = self.waypoints[
                        node_id - 1
                    ]

                    marker_item = MarkerItem(
                        "icons/marker.svg"
                    )

                    marker_item.setScale(
                        0.15
                    )

                    marker_item.setPos(
                        node.pos().x() - 5,
                        node.pos().y() - 12
                    )

                    self.scene.addItem(
                        marker_item
                    )

                except (
                    KeyError,
                    TypeError,
                    ValueError
                ):
                    continue

        regular_pen = QPen(
            QColor(0, 255, 0)
        )

        dual_pen = QPen(
            QColor(0, 0, 255)
        )

        reverse_pen = QPen(
            QColor(100, 220, 255)
        )

        for source_idx, connection_text in enumerate(
            out_connections
        ):
            if not connection_text.strip():
                continue

            if source_idx >= len(
                self.waypoints
            ):
                continue

            source = self.waypoints[
                source_idx
            ]

            targets = connection_text.split(",")

            for target_text in targets:
                try:
                    target_idx = int(
                        target_text
                    ) - 1

                    if target_idx < 0:
                        continue

                    if target_idx >= len(
                        self.waypoints
                    ):
                        continue

                    target = self.waypoints[
                        target_idx
                    ]

                    source_id = str(
                        source_idx + 1
                    )

                    target_id = str(
                        target_idx + 1
                    )

                    source_out = (
                        out_connections[source_idx]
                        .split(",")
                    )

                    source_in = (
                        in_connections[source_idx]
                        .split(",")
                    )

                    target_out = (
                        out_connections[target_idx]
                        .split(",")
                    )

                    target_in = (
                        in_connections[target_idx]
                        .split(",")
                    )

                    is_dual = (
                        target_id in source_out
                        and target_id in source_in
                        and source_id in target_out
                        and source_id in target_in
                    )

                    is_reverse = (
                        target_id in source_out
                        and source_id not in target_in
                    )

                    line = QGraphicsLineItem(
                        source.pos().x(),
                        source.pos().y(),
                        target.pos().x(),
                        target.pos().y()
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

                except (
                    IndexError,
                    ValueError
                ):
                    continue

        self.scene.setSceneRect(
            self.scene.itemsBoundingRect()
        )

        self.view.fitInView(
            self.scene.sceneRect(),
            Qt.KeepAspectRatio
        )

        self.status.setText(
            f"{count} Waypoints geladen"
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