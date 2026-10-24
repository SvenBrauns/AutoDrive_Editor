import xml.etree.ElementTree as ET

from PySide6.QtWidgets import (
    QMainWindow,
    QFileDialog,
    QComboBox,
    QGraphicsScene,
    QGraphicsEllipseItem,
    QGraphicsLineItem,
    QGraphicsPixmapItem,
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

from ui.map_view import MapView

from map.background_loader import (
    load_dds_as_pixmap
)
from map.background_transform import (
    MapTransform
)
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
        self.background_item = None

        # Standardmäßig Originalgröße
        self.map_scale = 1
        self.status = QLabel("Keine Datei geladen")

        self.node_info = QLabel(
            "Keine Node ausgewählt"
        )

        self.node_info.setMinimumWidth(250)

        btn_load = QPushButton("XML laden")
        btn_load.clicked.connect(self.load_xml)

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
            self.map_scale
        )

        if default_index >= 0:
            self.map_size_combo.setCurrentIndex(
                default_index
            )

        self.map_size_combo.currentIndexChanged.connect(
            self.on_map_scale_changed
        )


        top = QHBoxLayout()

        top.addWidget(btn_load)
        top.addWidget(map_size_label)
        top.addWidget(self.map_size_combo)
        top.addWidget(self.status)

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
        selected_scale = self.map_size_combo.itemData(index)

        if selected_scale is None:
            return

        self.map_scale = int(selected_scale)

        if self.background_item is not None:
            self.apply_background_transform()

            self.scene.setSceneRect(
                self.scene.itemsBoundingRect()
            )

    def apply_background_transform(self):
        if self.background_item is None:
            return

        pixmap = self.background_item.pixmap()

        if pixmap.isNull():
            return

        background_scale = (
            MapTransform.calculate_background_scale(
                self.map_scale
            )
        )

        pos_x, pos_z = (
            MapTransform.calculate_background_position(
                pixmap.width(),
                pixmap.height(),
                self.map_scale
            )
        )

        self.background_item.setScale(
            background_scale
        )

        self.background_item.setPos(
            pos_x,
            pos_z
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

        self.scene.clear()

        self.waypoints.clear()
        self.marker_data.clear()
        self.background_item = None

        tree = ET.parse(filename)
        root = tree.getroot()

        waypoint_section = root.find("waypoints")

        markers_section = root.find("markers")

        x_node = waypoint_section.find("x")
        y_node = waypoint_section.find("y")
        z_node = waypoint_section.find("z")

        if x_node is None or y_node is None or z_node is None:
            self.status.setText("x/y/z Daten fehlen")
            return

        xs = [float(v) for v in x_node.text.split(";") if v]
        ys = [float(v) for v in y_node.text.split(";") if v]
        zs = [float(v) for v in z_node.text.split(";") if v]

        try:
            self.create_background()

        except Exception as ex:
            print(
                "Background load failed:",
                ex
            )

        out_node = waypoint_section.find("out")

        if out_node is not None and out_node.text:
            out_connections = out_node.text.split(";")
        else:
            out_connections = []

        in_node = waypoint_section.find("in")

        if in_node is not None and in_node.text:
            in_connections = in_node.text.split(";")
        else:
            in_connections = []

        flags_node = waypoint_section.find("flags")
        
        if flags_node is not None and flags_node.text:
            flag_values = flags_node.text.split(";")
        else:
            flag_values = ["0"] * len(xs)

        markers_section = root.find("markers")

        count = min(
            len(xs),
            len(ys),
            len(zs),
            len(flag_values)
        )

        for i in range(count):

            item = NodeItem(
                i + 1,
                xs[i],
                ys[i],
                zs[i],
                int(flag_values[i]),
                self
            )

            self.scene.addItem(item)

            self.waypoints.append(item)

        if markers_section is not None:

            for marker in markers_section:

                try:

                    node_id = int(marker.attrib["i"])

                    marker_name = marker.attrib.get("n", "")

                    marker_group = marker.attrib.get("g", "")

                    self.marker_data[node_id] = {
                        "name": marker_name,
                        "group": marker_group
                    }

                    if node_id <= 0:
                        continue

                    if node_id > len(self.waypoints):
                        continue

                    node = self.waypoints[node_id - 1]

                    marker_item = MarkerItem(
                        "icons/marker.svg"
                    )

                    marker_item.setScale(0.15)

                    marker_item.setPos(
                        node.pos().x() - 5,
                        node.pos().y() - 12
                    )

                    self.scene.addItem(marker_item)

                except Exception:
                    pass

        regular_pen = QPen(QColor(0, 255, 0))   # Grün
        dual_pen = QPen(QColor(0, 0, 255))      # Blau
        reverse_pen = QPen(QColor(100, 220, 255)) # Hellblau

        MAX_CONNECTIONS = len(out_connections)

        for source_idx, connection_text in enumerate(out_connections[:MAX_CONNECTIONS]):

            if not connection_text.strip():
                continue

            source = self.waypoints[source_idx]

            targets = connection_text.split(",")

            for target_text in targets:

                try:
                    target_idx = int(target_text) - 1

                    if target_idx < 0:
                        continue

                    if target_idx >= len(self.waypoints):
                        continue

                    target = self.waypoints[target_idx]

                    source_id = str(source_idx + 1)
                    target_id = str(target_idx + 1)

                    source_out = out_connections[source_idx].split(",")
                    source_in = in_connections[source_idx].split(",")

                    target_out = out_connections[target_idx].split(",")
                    target_in = in_connections[target_idx].split(",")
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
                        line.setPen(dual_pen)
                    elif is_reverse:
                        line.setPen(reverse_pen)
                    else:
                        line.setPen(regular_pen)

                    self.scene.addItem(line)

                except ValueError:
                    pass

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

    def create_background(self):
        pixmap = load_dds_as_pixmap(
            "maps/TestMap/overview.dds"
        )

        if pixmap.isNull():
            raise ValueError(
                "Die Hintergrundkarte konnte nicht geladen werden."
            )

        self.background_item = QGraphicsPixmapItem(
            pixmap
        )

        self.background_item.setZValue(
            -1000
        )

        self.scene.addItem(
            self.background_item
        )

        self.apply_background_transform()