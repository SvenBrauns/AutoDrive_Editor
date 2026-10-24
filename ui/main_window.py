from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow,
    QFileDialog,
    QGraphicsScene,
    QWidget,
    QLabel,
    QHBoxLayout,
    QToolBar
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
from map.heightmap_manager import HeightmapManager
from project.project_manager import ProjectManager
from rendering.scene_renderer import SceneRenderer
from ui.map_view import MapView
from ui.interaction_mode import InteractionMode
from items.node_item import NodeItem

class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("AutoDrive FS25 Editor")
        self.resize(1400, 900)

        self.scene = QGraphicsScene()

        self.view = MapView()
        self.view.setScene(self.scene)
        self.autodrive_data = None
        self.selected_node_data = None

        self.background_manager = BackgroundManager(
            self.scene,
            map_scale=1
        )

        self.heightmap_manager = HeightmapManager()

        self.scene_renderer = SceneRenderer(
            self.scene,
            MARKER_ICON_PATH
        )

        self.view.zoom_changed.connect(
            self.scene_renderer.update_visibility_for_zoom
        ) 

        self.view.visible_scene_rect_changed.connect(
            self.scene_renderer.update_visible_scene_rect
        )

        self.view.selection_click_requested.connect(
            self.handle_selection_click
        )
  
        self.config_directory = CONFIG_DIRECTORY

        self.project_manager = ProjectManager(
            self.config_directory
        )

        self.create_interaction_actions()
        self.create_menu_bar()
        self.create_quick_access_toolbar()
        self.create_editor_toolbar()

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
            self.status.setText(
                f"Heightmap konnte nicht geladen werden: {ex}"
            )
            return

        self.current_heightmap_path = str(
            heightmap_data.file_path
        )

        self.remove_heightmap_action.setEnabled(
            True
        )

        self.status.setText(
            f"Heightmap geladen: "
            f"{heightmap_data.width} × "
            f"{heightmap_data.height}, "
            f"{heightmap_data.format_description}"
        )

        self._refresh_selected_node_info()

    def remove_heightmap(self):
        self.heightmap_manager.clear()

        self.current_heightmap_path = None

        self.remove_heightmap_action.setEnabled(
            False
        )

        self.status.setText(
            "Heightmap entfernt"
        )

        self._refresh_selected_node_info()

    def create_interaction_actions(self):
        self.navigation_action = QAction(
            "Navigation",
            self
        )

        self.navigation_action.setCheckable(
            True
        )

        self.navigation_action.setToolTip(
            "Kartenansicht verschieben und drehen"
        )

        self.navigation_action.triggered.connect(
            self.activate_navigation_mode
        )

        self.selection_action = QAction(
            "Auswahl",
            self
        )

        self.selection_action.setCheckable(
            True
        )

        self.selection_action.setToolTip(
            "Nodes und Connections auswählen"
        )

        self.selection_action.triggered.connect(
            self.activate_selection_mode
        )

        self.interaction_action_group = QActionGroup(
            self
        )

        self.interaction_action_group.setExclusive(
            True
        )

        self.interaction_action_group.addAction(
            self.navigation_action
        )

        self.interaction_action_group.addAction(
            self.selection_action
        )

        self.navigation_action.setChecked(
            True
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

        select_heightmap_action = QAction(
            "Heightmap auswählen",
            self
        )

        select_heightmap_action.triggered.connect(
            self.select_heightmap
        )

        map_menu.addAction(
            select_heightmap_action
        )

        self.remove_heightmap_action = QAction(
            "Heightmap entfernen",
            self
        )

        self.remove_heightmap_action.triggered.connect(
            self.remove_heightmap
        )

        self.remove_heightmap_action.setEnabled(
            False
        )

        map_menu.addAction(
            self.remove_heightmap_action
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

        view_menu = menu_bar.addMenu(
            "Ansicht"
        )

        display_options_action = QAction(
            "Darstellungsoptionen...",
            self
        )

        display_options_action.setEnabled(
            False
        )

        view_menu.addAction(
            display_options_action
        )

        view_menu.addSeparator()

        debug_view_action = QAction(
            "Debuganzeige",
            self
        )

        debug_view_action.setCheckable(
            True
        )

        debug_view_action.setChecked(
            True
        )

        debug_view_action.setEnabled(
            False
        )

        view_menu.addAction(
            debug_view_action
        )

        view_menu.addSeparator()

        reset_view_action = QAction(
            "Ansicht zurücksetzen",
            self
        )

        reset_view_action.setEnabled(
            False
        )

        view_menu.addAction(
            reset_view_action
        )

        reset_rotation_action = QAction(
            "Rotation zurücksetzen",
            self
        )

        reset_rotation_action.setEnabled(
            False
        )

        view_menu.addAction(
            reset_rotation_action
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
        self.selected_node_data = None

        self.node_info.setText(
            "Keine Node ausgewählt"
        )

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

            self.selected_node_data = None

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

                self.current_heightmap_path = str(
                    heightmap_data.file_path
                )

                self.remove_heightmap_action.setEnabled(
                    True
                )

            else:
                self.heightmap_manager.clear()

                self.current_heightmap_path = None

                self.remove_heightmap_action.setEnabled(
                    False
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

        project_name = Path(
            config_path
        ).name

        if self.heightmap_manager.has_heightmap():
            self.status.setText(
                f"Projekt geladen: {project_name} "
                f"mit Heightmap"
            )

        else:
            self.status.setText(
                f"Projekt geladen: {project_name}"
            )

    def _refresh_selected_node_info(self):
        if self.selected_node_data is None:
            return

        self.show_node_info(
            self.selected_node_data
        )

    def show_node_info(self, node_data):
        self.selected_node_data = node_data

        self.scene_renderer.select_node(
            node_data
        )

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

        marker_lines = []

        if marker_data is not None:
            marker_lines.extend(
                [
                    "",
                    f"Marker: {marker_data.name}",
                    f"Gruppe: {marker_data.group}"
                ]
            )

        heightmap_lines = []

        if self.heightmap_manager.has_heightmap():
            try:
                height_sample = (
                    self.heightmap_manager.get_height_at(
                        world_x=node_data.x,
                        world_z=node_data.z,
                        map_scale=(
                            self.background_manager.map_scale
                        )
                    )
                )

                height_difference = (
                    height_sample.height
                    - node_data.y
                )

                heightmap_lines.extend(
                    [
                        "",
                        f"Y laut XML: {node_data.y:.3f}",
                        (
                            f"Y laut Heightmap: "
                            f"{height_sample.height:.3f}"
                        ),
                        (
                            f"Abweichung: "
                            f"{height_difference:+.3f}"
                        ),
                        (
                            f"Heightmap-Pixel: "
                            f"{height_sample.pixel_x}, "
                            f"{height_sample.pixel_y}"
                        ),
                        (
                            f"Heightmap-Rohwert: "
                            f"{height_sample.raw_value}"
                        )
                    ]
                )

            except ValueError as ex:
                heightmap_lines.extend(
                    [
                        "",
                        "Heightmap-Auswertung nicht möglich:",
                        str(ex)
                    ]
                )

        else:
            heightmap_lines.extend(
                [
                    "",
                    f"Y: {node_data.y:.3f}"
                ]
            )

        info_lines = [
            f"Node ID: {node_data.node_id}",
            "",
            f"Typ: {node_type}",
            *marker_lines,
            "",
            f"X: {node_data.x:.3f}",
            *heightmap_lines,
            f"Z: {node_data.z:.3f}"
        ]

        self.node_info.setText(
            "\n".join(info_lines)
        )

    def activate_navigation_mode(
        self,
        checked
    ):
        if not checked:
            return

        self.set_interaction_mode(
            InteractionMode.NAVIGATE
        )


    def activate_selection_mode(
        self,
        checked
    ):
        if not checked:
            return

        self.set_interaction_mode(
            InteractionMode.SELECT
        )


    def set_interaction_mode(
        self,
        interaction_mode: InteractionMode
    ):
        self.view.set_interaction_mode(
            interaction_mode
        )

        if interaction_mode == InteractionMode.NAVIGATE:
            self.status.setText(
                "Modus: Navigation"
            )

        elif interaction_mode == InteractionMode.SELECT:
            self.status.setText(
                "Modus: Auswahl"
            )

    def create_quick_access_toolbar(self):
        self.quick_access_toolbar = QToolBar(
            "Schnellauswahl",
            self
        )

        self.quick_access_toolbar.setObjectName(
            "quick_access_toolbar"
        )

        self.quick_access_toolbar.setMovable(
            False
        )

        self.quick_access_toolbar.setFloatable(
            False
        )

        self.quick_access_toolbar.setToolButtonStyle(
            Qt.ToolButtonTextOnly
        )

        self.addToolBar(
            Qt.TopToolBarArea,
            self.quick_access_toolbar
        )

        self.quick_access_toolbar.addAction(
            self.navigation_action
        )

        self.quick_access_toolbar.addAction(
            self.selection_action
        )

    def create_editor_toolbar(self):
        self.editor_toolbar = QToolBar(
            "Editor-Werkzeuge",
            self
        )

        self.editor_toolbar.setObjectName(
            "editor_toolbar"
        )

        self.editor_toolbar.setMovable(
            False
        )

        self.editor_toolbar.setFloatable(
            False
        )

        self.editor_toolbar.setToolButtonStyle(
            Qt.ToolButtonTextUnderIcon
        )

        self.addToolBar(
            Qt.LeftToolBarArea,
            self.editor_toolbar
        )

        placeholder_action = QAction(
            "Editor",
            self
        )

        placeholder_action.setEnabled(
            False
        )

        placeholder_action.setToolTip(
            "Editor-Werkzeuge werden später ergänzt"
        )

        self.editor_toolbar.addAction(
            placeholder_action
        )

    def handle_selection_click(
        self,
        view_position,
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

        self.selected_node_data = None

        self.scene_renderer.clear_selection()

        self.node_info.setText(
            "Keine Node ausgewählt"
        )