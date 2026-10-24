from PySide6.QtCore import Qt
from PySide6.QtGui import (
    QAction,
    QActionGroup
)
from PySide6.QtWidgets import (
    QMainWindow,
    QToolBar
)

from ui.interaction_mode import InteractionMode


class MainWindowActions:

    MAP_SCALES = (
        ("Originalgröße", 1),
        ("4x-Karte", 2),
        ("16x-Karte", 4),
        ("64x-Karte", 8)
    )

    def __init__(
        self,
        window: QMainWindow
    ):
        self.window = window

        self.map_scale_actions = {}

        self._create_actions()
        self._create_menu_bar()
        self._create_quick_access_toolbar()
        self._create_editor_toolbar()

    def _create_actions(self):
        self.navigation_action = QAction(
            "Navigation",
            self.window
        )

        self.navigation_action.setCheckable(
            True
        )

        self.navigation_action.setToolTip(
            "Kartenansicht verschieben und drehen"
        )

        self.navigation_action.triggered.connect(
            self._activate_navigation_mode
        )

        self.selection_action = QAction(
            "Auswahl",
            self.window
        )

        self.selection_action.setCheckable(
            True
        )

        self.selection_action.setToolTip(
            "Nodes und Connections auswählen"
        )

        self.selection_action.triggered.connect(
            self._activate_selection_mode
        )

        self.interaction_action_group = QActionGroup(
            self.window
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

        self.load_project_action = QAction(
            "Projekt laden",
            self.window
        )

        self.load_project_action.triggered.connect(
            self.window.load_project
        )

        self.save_project_action = QAction(
            "Projekt speichern",
            self.window
        )

        self.save_project_action.triggered.connect(
            self.window.save_project
        )

        self.load_xml_action = QAction(
            "AutoDrive-XML laden",
            self.window
        )

        self.load_xml_action.triggered.connect(
            self.window.load_xml
        )

        self.exit_action = QAction(
            "Beenden",
            self.window
        )

        self.exit_action.triggered.connect(
            self.window.close
        )

        self.display_options_action = QAction(
            "Darstellungsoptionen...",
            self.window
        )

        self.display_options_action.setEnabled(
            False
        )

        self.reset_view_action = QAction(
            "Ansicht zurücksetzen",
            self.window
        )

        self.reset_view_action.setEnabled(
            False
        )

        self.reset_rotation_action = QAction(
            "Rotation zurücksetzen",
            self.window
        )

        self.reset_rotation_action.setEnabled(
            False
        )

        self.reset_rotation_action.triggered.connect(
            self.window.reset_view_rotation
        )

        self.select_background_action = QAction(
            "DDS auswählen",
            self.window
        )

        self.select_background_action.triggered.connect(
            self.window.select_background
        )

        self.select_heightmap_action = QAction(
            "Heightmap auswählen",
            self.window
        )

        self.select_heightmap_action.triggered.connect(
            self.window.select_heightmap
        )

        self.remove_heightmap_action = QAction(
            "Heightmap entfernen",
            self.window
        )

        self.remove_heightmap_action.triggered.connect(
            self.window.remove_heightmap
        )

        self.remove_heightmap_action.setEnabled(
            False
        )

        self._create_map_scale_actions()

    def _create_map_scale_actions(self):
        self.map_scale_action_group = QActionGroup(
            self.window
        )

        self.map_scale_action_group.setExclusive(
            True
        )

        for label, map_scale in self.MAP_SCALES:
            action = QAction(
                label,
                self.window
            )

            action.setCheckable(
                True
            )

            action.setData(
                map_scale
            )

            action.triggered.connect(
                lambda checked, selected_scale=map_scale:
                self.window.set_map_scale(
                    selected_scale
                )
                if checked
                else None
            )

            self.map_scale_action_group.addAction(
                action
            )

            self.map_scale_actions[
                map_scale
            ] = action

    def _create_menu_bar(self):
        menu_bar = self.window.menuBar()

        file_menu = menu_bar.addMenu(
            "Datei"
        )

        file_menu.addAction(
            self.load_project_action
        )

        file_menu.addAction(
            self.save_project_action
        )

        file_menu.addSeparator()

        file_menu.addAction(
            self.load_xml_action
        )

        file_menu.addSeparator()

        file_menu.addAction(
            self.exit_action
        )

        view_menu = menu_bar.addMenu(
            "Ansicht"
        )

        view_menu.addAction(
            self.display_options_action
        )

        view_menu.addSeparator()

        view_menu.addAction(
            self.window.debug_dock.toggleViewAction()
        )

        view_menu.addSeparator()

        view_menu.addAction(
            self.reset_view_action
        )

        view_menu.addAction(
            self.reset_rotation_action
        )

        map_menu = menu_bar.addMenu(
            "Karte"
        )

        map_menu.addAction(
            self.select_background_action
        )

        map_menu.addSeparator()

        map_menu.addAction(
            self.select_heightmap_action
        )

        map_menu.addAction(
            self.remove_heightmap_action
        )

        map_menu.addSeparator()

        map_size_menu = map_menu.addMenu(
            "Kartengröße"
        )

        for _, map_scale in self.MAP_SCALES:
            map_size_menu.addAction(
                self.map_scale_actions[
                    map_scale
                ]
            )

    def _create_quick_access_toolbar(self):
        self.quick_access_toolbar = QToolBar(
            "Schnellauswahl",
            self.window
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

        self.window.addToolBar(
            Qt.TopToolBarArea,
            self.quick_access_toolbar
        )

        self.quick_access_toolbar.addAction(
            self.navigation_action
        )

        self.quick_access_toolbar.addAction(
            self.selection_action
        )

    def _create_editor_toolbar(self):
        self.editor_toolbar = QToolBar(
            "Editor-Werkzeuge",
            self.window
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

        self.window.addToolBar(
            Qt.LeftToolBarArea,
            self.editor_toolbar
        )

        self.editor_placeholder_action = QAction(
            "Editor",
            self.window
        )

        self.editor_placeholder_action.setEnabled(
            False
        )

        self.editor_placeholder_action.setToolTip(
            "Editor-Werkzeuge werden später ergänzt"
        )

        self.editor_toolbar.addAction(
            self.editor_placeholder_action
        )

    def set_current_map_scale(
        self,
        map_scale: int
    ):
        action = self.map_scale_actions.get(
            map_scale
        )

        if action is not None:
            action.setChecked(
                True
            )

    def _activate_navigation_mode(
        self,
        checked: bool
    ):
        if not checked:
            return

        self.window.set_interaction_mode(
            InteractionMode.NAVIGATE
        )

    def _activate_selection_mode(
        self,
        checked: bool
    ):
        if not checked:
            return

        self.window.set_interaction_mode(
            InteractionMode.SELECT
        )