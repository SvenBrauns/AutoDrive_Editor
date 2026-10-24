import xml.etree.ElementTree as ET

from PySide6.QtWidgets import (
    QMainWindow,
    QFileDialog,
    QComboBox,
    QGraphicsScene,
    QGraphicsEllipseItem,
    QGraphicsLineItem,
    QWidget,
    QVBoxLayout,
    QPushButton,
    QLabel,
    QHBoxLayout
)

from PySide6.QtGui import (
    QBrush,
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

        self.current_xml_path = None
        self.current_config_path = None
        self.current_heightmap_path = None

        self.status = QLabel("Keine Datei geladen")

        self.node_info = QLabel(
            "Keine Node ausgewählt"
        )

        self.node_info.setMinimumWidth(250)

        btn_load = QPushButton("XML laden")
        btn_load.clicked.connect(self.load_xml)

        btn_background = QPushButton("DDS auswählen")
        btn_background.clicked.connect(
            self.select_background
        )

        btn_load_project = QPushButton(
            "Projekt laden"
        )

        btn_load_project.clicked.connect(
            self.load_project
        )

        btn_save_project = QPushButton(
            "Projekt speichern"
        )

        btn_save_project.clicked.connect(
            self.save_project
        )

        map_size_label = QLabel("Kartengröße:")

        self.map_size_combo = QComboBox()

        self.map_size_combo.addItem(
            "Originalgröße",
            1
        )

        self.map_size_combo.addItem(
            "4x-Karte",
            2
        )

        self.map_size_combo.addItem(
            "16x-Karte",
            4
        )

        self.map_size_combo.addItem(
            "64x-Karte",
            8
        )

        default_index = self.map_size_combo.findData(
            self.background_manager.map_scale
        )

        if default_index >= 0:
            self.map_size_combo.setCurrentIndex(
                default_index
            )

        self.map_size_combo.currentIndexChanged.connect(
            self.on_map_scale_changed
        )


        top = QHBoxLayout()

        top.addWidget(
            btn_load_project
        )

        top.addWidget(
            btn_save_project
        )

        top.addWidget(
            btn_load
        )

        top.addWidget(
            btn_background
        )

        top.addWidget(
            map_size_label
        )

        top.addWidget(
            self.map_size_combo
        )

        top.addWidget(
            self.status
        )

        top.addStretch()

        main_layout = QHBoxLayout()

        left_layout = QVBoxLayout()
        left_layout.addLayout(top)
        left_layout.addWidget(self.view)

        main_layout.addLayout(left_layout)
        main_layout.addWidget(self.node_info)

        container = QWidget()
        container.setLayout(main_layout)

        self.setCentralWidget(container)
        self.view.setScene(self.scene)

    def on_map_scale_changed(self, index):
        selected_scale = self.map_size_combo.itemData(
            index
        )

        if selected_scale is None:
            return

        try:
            self.background_manager.set_map_scale(
                selected_scale
            )

        except Exception as ex:
            self.status.setText(
                f"Kartengröße konnte nicht geändert werden: {ex}"
            )

            return

        self.scene.setSceneRect(
            self.scene.itemsBoundingRect()
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

            scale_index = (
                self.map_size_combo.findData(
                    map_scale
                )
            )

            if scale_index < 0:
                raise ValueError(
                    f"Unbekannte Kartengröße: {map_scale}"
                )

            self.map_size_combo.setCurrentIndex(
                scale_index
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