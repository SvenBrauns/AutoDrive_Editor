from PySide6.QtCore import Qt
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (
    QApplication,
    QGraphicsScene,
    QInputDialog,
    QLabel,
    QMainWindow,
    QVBoxLayout,
)

from autodrive_editor.editing.commands.edit_command import DataChange
from autodrive_editor.editing.edit_context import EditContext
from autodrive_editor.editing.edit_history import EditHistory
from autodrive_editor.editing.operations.align_nodes import AlignNodesOperation
from autodrive_editor.editing.operations.clipboard import ClipboardOperation
from autodrive_editor.editing.operations.connect_nodes import ConnectNodesOperation
from autodrive_editor.editing.operations.create_nodes import CreateNodesOperation
from autodrive_editor.editing.operations.create_path import CreatePathOperation
from autodrive_editor.editing.operations.delete_nodes import DeleteNodesOperation
from autodrive_editor.editing.operations.markers import MarkerOperation
from autodrive_editor.editing.operations.move_nodes import MoveNodesOperation
from autodrive_editor.editing.operations.network_check import NetworkCheckOperation
from autodrive_editor.editing.operations.node_position import NodePositionOperation
from autodrive_editor.editing.operations.node_types import NodeTypeOperation
from autodrive_editor.editing.operations.parking_spots import ParkingSpotOperation
from autodrive_editor.editing.operations.reverse_direction import ReverseDirectionOperation
from autodrive_editor.editing.operations.rotate_selection import RotateSelectionOperation
from autodrive_editor.editing.path_shapes import PathShape
from autodrive_editor.file_io.autodrive_xml import ConfigFormat
from autodrive_editor.file_io.game_files import GameFiles
from autodrive_editor.file_io.project_file import ProjectFileStore
from autodrive_editor.i18n import tr
from autodrive_editor.measurement.coordinator import MeasurementCoordinator
from autodrive_editor.measurement.mode import MeasurementMode
from autodrive_editor.model.autodrive_data import (
    REGULAR_FLAG,
    SUBPRIO_FLAG,
    AutoDriveData,
    NodeData,
)
from autodrive_editor.model.connections import ConnectionType
from autodrive_editor.network_check.ignores import IgnoreStore
from autodrive_editor.paths import MARKER_ICON_PATH, local_projects_directory, user_data_directory
from autodrive_editor.project.autosave import AutosaveStore
from autodrive_editor.project.project_coordinator import ProjectCoordinator
from autodrive_editor.rendering.display_style import DisplayStyle
from autodrive_editor.rendering.scene_renderer import SceneRenderer
from autodrive_editor.rendering.visibility import Visibility
from autodrive_editor.selection.node_selection import NodeSelection
from autodrive_editor.selection.selection_coordinator import SelectionCoordinator
from autodrive_editor.settings.app_settings import AppSettings
from autodrive_editor.terrain.background_map import BackgroundMap
from autodrive_editor.terrain.heightmap import Heightmap
from autodrive_editor.terrain.map_cache import MapCache
from autodrive_editor.ui.actions.main_window_actions import MainWindowActions
from autodrive_editor.ui.controls.grid_coordinator import GridCoordinator
from autodrive_editor.ui.dialogs.marker_dialog import MarkerDialog
from autodrive_editor.ui.dialogs.messages import APP_TITLE
from autodrive_editor.ui.dialogs.node_position_dialog import NodePositionDialog
from autodrive_editor.ui.dialogs.parking_spot_dialog import ParkingSpotDialog
from autodrive_editor.ui.dialogs.settings_dialog import SettingsDialog
from autodrive_editor.ui.file_controller import FileController
from autodrive_editor.ui.map_import_controller import MapImportController
from autodrive_editor.ui.map_view.map_view import MapView
from autodrive_editor.ui.map_view.rotation_controller import ViewRotationController
from autodrive_editor.ui.network_check_controller import NetworkCheckController
from autodrive_editor.ui.panels.check_dock import CheckDock
from autodrive_editor.ui.panels.debug_dock import DebugDock
from autodrive_editor.ui.panels.debug_dock_coordinator import DebugDockCoordinator
from autodrive_editor.ui.panels.display_options_dialog import DisplayOptionsDialog
from autodrive_editor.ui.panels.marker_dock import MarkerDock
from autodrive_editor.ui.panels.node_info_formatter import NodeInfoFormatter
from autodrive_editor.ui.panels.path_options import PathOptionsWidget
from autodrive_editor.ui.panels.rotate_options import RotateOptionsWidget
from autodrive_editor.ui.panels.welcome_panel import WelcomePanel
from autodrive_editor.ui.savegame_link_controller import SavegameLinkController
from autodrive_editor.ui.theme import apply_theme
from autodrive_editor.ui.tools.connect_nodes_tool import ConnectNodesTool
from autodrive_editor.ui.tools.create_node_tool import CreateNodeTool
from autodrive_editor.ui.tools.delete_nodes_tool import DeleteNodesTool
from autodrive_editor.ui.tools.interaction_mode import InteractionMode
from autodrive_editor.ui.tools.measure_tool import MeasureTool
from autodrive_editor.ui.tools.move_nodes_tool import MoveNodesTool
from autodrive_editor.ui.tools.node_click_tool import NodeClickTool
from autodrive_editor.ui.tools.path_tool import PathTool
from autodrive_editor.ui.tools.rotate_selection_tool import RotateSelectionTool
from autodrive_editor.ui.tools.select_tool import SelectTool
from autodrive_editor.ui.tools.toggle_node_type_tool import ToggleNodeTypeTool
from autodrive_editor.ui.update_controller import UpdateController


class MainWindow(QMainWindow):
    """The editor window. It creates all parts of the editor and wires
    them together:

    1. scene and map view
    2. map layers: background, heightmap, renderer, project files
    3. selection and measurement
    4. edit history and edit operations, then the map tools using them
    5. project coordinator, which loads data into all of the above
    6. widgets, actions, menus and toolbars, then the signal wiring
    """

    WINDOW_TITLE = APP_TITLE
    INITIAL_WIDTH = 1400
    INITIAL_HEIGHT = 900

    NO_FILE_STATUS = tr("No file loaded")
    NO_SELECTION_INFO = tr("No node selected")

    DEFAULT_MAP_SCALE = 1

    # How far from a connection line a click still hits it, in pixels.
    CONNECTION_CLICK_TOLERANCE = 6.0

    # Zoom used when jumping to a marker from the marker list.
    FOCUS_MARKER_ZOOM = 2.0

    def __init__(self):
        super().__init__()

        self.local_projects_directory = local_projects_directory()

        # Detects the FS25 folder on first start and keeps it afterwards.
        self.settings = AppSettings()
        self.settings.ensure_game_folder()
        self.settings.ensure_install_folder()

        # Map images and heightmaps imported from map mods.
        self.map_cache = MapCache()

        self._configure_window()
        self._create_scene_and_view()

        self._create_map_layers()
        self._create_selection_and_measurement()
        self._create_edit_operations()
        self._register_map_tools()
        self._create_project_coordinator()
        self._create_file_controllers()

        self._create_status_widgets()
        self._create_central_widget()
        self._create_marker_dock()
        self._create_check_dock()
        self._create_debug_dock()

        self.scene_renderer.set_marker_names_visible(self.settings.marker_names_visible)
        self.scene_renderer.set_visibility(self.settings.visibility)

        self.actions = MainWindowActions(self)
        self.actions.set_current_map_scale(self.background_map.map_scale)
        self._create_tool_options()

        self._create_welcome_panel()
        self._create_grid_coordinator()
        self._connect_signals()

        # Created after the renderer is connected to the view, so the
        # dock reads the renderer state after it has been updated.
        self._create_debug_dock_coordinator()

    def set_map_scale(self, map_scale: int):
        action = self.actions.map_scale_actions.get(map_scale)

        map_scale_label = action.text() if action is not None else str(map_scale)

        try:
            self.project_coordinator.set_map_scale(
                map_scale=map_scale, map_scale_label=map_scale_label
            )

        except Exception as ex:
            self._set_status(tr("The map size could not be changed: {error}", error=ex))

    def closeEvent(self, event):
        if self.files.confirm_discard_changes():
            event.accept()
        else:
            event.ignore()

    def show_node_info(self, node_data: NodeData):
        self.selection_coordinator.show_node_info(node_data)

    def set_interaction_mode(self, interaction_mode: InteractionMode):
        self.view.set_interaction_mode(interaction_mode)

        status_text = tr("Mode: {mode}", mode=interaction_mode.display_name)

        status_hint = self.view.active_tool.status_hint()

        if status_hint:
            status_text += f" – {status_hint}"

        self._set_status(status_text)

    def set_view_rotation(self, rotation_angle: float):
        self.view.set_rotation_angle(rotation_angle)

        self._set_status(tr("Rotation: {angle:.2f}°", angle=self.view.rotation_angle))

    def set_view_rotation_step(self, rotation_step: float):
        self.view.set_rotation_step(rotation_step)

        self._set_status(tr("Rotation step: {angle:.2f}°", angle=self.view.rotation_step))

    def reset_view_rotation(self):
        self.view.reset_view_rotation()

        self._set_status(tr("Rotation reset"))

    def set_measurement_mode(self, measurement_mode: MeasurementMode):
        self.measurement_coordinator.set_mode(measurement_mode)

    def delete_selection(self):
        self.delete_nodes_operation.delete_selection()

    def align_view_to_measurement(self):
        self.measurement_coordinator.align_view_to_measurement()

    def open_settings(self):
        dialog = SettingsDialog(self.settings, self.actions.shortcuts, parent=self)

        if dialog.exec():
            self.files.apply_autosave_interval()
            self.actions.apply_shortcuts(self.settings.shortcuts)
            apply_theme(QApplication.instance(), self.settings.theme)

            folder = self.settings.game_folder

            if folder is None:
                self._set_status(tr("No game folder set"))
            elif folder.is_valid:
                self._set_status(tr("Game folder: {path}", path=folder.path))
            else:
                self._set_status(
                    tr("The game folder is not an FS25 user folder: {path}", path=folder.path)
                )

    def set_marker_names_visible(self, visible: bool):
        self.scene_renderer.set_marker_names_visible(visible)
        self.settings.set_marker_names_visible(visible)

    def set_visibility(self, visibility: Visibility):
        self.scene_renderer.set_visibility(visibility)
        self.settings.set_visibility(visibility)

    def focus_marker(self, node_id: int):
        """Centers the map on a marker's node and selects it."""

        self.focus_nodes([node_id])

    def focus_nodes(self, node_ids: list[int]):
        """Centers the map on the first of the nodes and selects them.
        Nodes that no longer exist are left out."""

        autodrive_data = self._get_autodrive_data()

        if autodrive_data is None:
            return

        node_ids = [node_id for node_id in node_ids if node_id in autodrive_data.nodes]

        if not node_ids:
            return

        node = autodrive_data.nodes[node_ids[0]]

        # Zoom in far enough to see the node.
        if self.view.zoom_level < self.FOCUS_MARKER_ZOOM:
            self.view.set_zoom_level(self.FOCUS_MARKER_ZOOM)

        self.view.centerOn(node.x, node.z)
        self.node_selection.replace(set(node_ids), node.node_id)

    def rename_marker_group(self, name: str):
        new_name = self._ask_group_name(name)

        if new_name is not None:
            self.marker_operation.rename_group(name, new_name)

    def _ask_group_name(self, name: str) -> str | None:
        new_name, accepted = QInputDialog.getText(
            self, tr("Rename marker group"), tr("New name:"), text=name
        )

        return new_name if accepted else None

    def _ask_node_position(self, node):
        dialog = NodePositionDialog(node.node_id, node.x, node.y, node.z, parent=self)

        return dialog.values if dialog.exec() else None

    def _ask_parking_settings(self, area, autodrive_data):
        taken_names = {(marker.name, marker.group) for marker in autodrive_data.markers.values()}
        dialog = ParkingSpotDialog(
            area, autodrive_data.marker_group_names(), taken_names, self.settings, parent=self
        )

        return dialog.settings if dialog.exec() else None

    def _ask_marker(self, title, marker, group, groups, taken_names):
        dialog = MarkerDialog(
            title,
            marker.name if marker is not None else "",
            group,
            groups,
            taken_names,
            parent=self,
        )

        return dialog.values if dialog.exec() else None

    def open_display_options(self):
        dialog = DisplayOptionsDialog(display_style=self.scene_renderer.display_style, parent=self)

        dialog.style_applied.connect(self.apply_display_style)

        dialog.exec()

    def apply_display_style(self, display_style: DisplayStyle):
        if not isinstance(display_style, DisplayStyle):
            raise TypeError("Invalid display style.")

        self.scene_renderer.set_display_style(display_style)

        self._set_status(tr("Display options applied"))

    def _configure_window(self):
        # Qt shows "*" in place of "[*]" while the window is modified.
        self.setWindowTitle(f"{self.WINDOW_TITLE}[*]")

        self.resize(self.INITIAL_WIDTH, self.INITIAL_HEIGHT)

    def _create_scene_and_view(self):
        self.scene = QGraphicsScene()

        self.view = MapView()

        self.view.setScene(self.scene)

    def _create_map_layers(self):
        """Background map, heightmap, node rendering and project files."""

        self.background_map = BackgroundMap(self.scene, map_scale=self.DEFAULT_MAP_SCALE)

        self.heightmap = Heightmap()

        self.node_info_formatter = NodeInfoFormatter(
            background_map=self.background_map, heightmap=self.heightmap
        )

        self.scene_renderer = SceneRenderer(self.scene, MARKER_ICON_PATH)

        self.project_files = ProjectFileStore(self.local_projects_directory)

    def _create_selection_and_measurement(self):
        self.node_selection = NodeSelection()

        self.selection_coordinator = SelectionCoordinator(
            view=self.view,
            renderer=self.scene_renderer,
            node_selection=self.node_selection,
            node_info_formatter=self.node_info_formatter,
            autodrive_data_provider=self._get_autodrive_data,
            parent=self,
        )

        self.view.set_node_finder(self.selection_coordinator.get_node_at)

        self.measurement_coordinator = MeasurementCoordinator(
            view=self.view,
            scene=self.scene,
            node_provider=self.selection_coordinator.get_node_at,
            parent=self,
        )

    def _create_edit_operations(self):
        """The undo history and every operation that changes the data."""

        self.edit_history = EditHistory(parent=self)

        context = EditContext(
            edit_history=self.edit_history,
            autodrive_data_provider=self._get_autodrive_data,
            view=self.view,
            selection_coordinator=self.selection_coordinator,
            node_selection=self.node_selection,
            terrain_height_at=self._get_terrain_height,
            snap_point=self.background_map.snap_point,
            grid_rotation=lambda: self.background_map.grid_rotation,
        )

        self.move_nodes_operation = MoveNodesOperation(context, parent=self)
        self.delete_nodes_operation = DeleteNodesOperation(context, parent=self)
        self.connect_nodes_operation = ConnectNodesOperation(context, parent=self)
        self.rotate_selection_operation = RotateSelectionOperation(context, parent=self)
        self.rotate_selection_operation.snap_angle = self.settings.rotate_snap_angle
        self.create_nodes_operation = CreateNodesOperation(context, parent=self)
        self.node_type_operation = NodeTypeOperation(context, parent=self)
        self.align_nodes_operation = AlignNodesOperation(context, parent=self)

        self.create_path_operation = CreatePathOperation(
            context,
            height_for_new_node=self.create_nodes_operation.height_for_new_node,
            parent=self,
        )
        self.create_path_operation.set_options(self.settings.path_options)

        self.clipboard_operation = ClipboardOperation(
            context,
            delete_nodes=self.delete_nodes_operation.delete_nodes,
            # Looked up on each call, so tests can replace it.
            paste_position=lambda: self._get_paste_position(),
            parent=self,
        )

        self.node_position_operation = NodePositionOperation(
            context,
            # Looked up on each call, so tests can replace _ask_node_position.
            ask_position=lambda node: self._ask_node_position(node),
            parent=self,
        )

        self.parking_spot_operation = ParkingSpotOperation(
            context,
            shed_at=self._get_shed_at,
            # Looked up on each call, so tests can replace _ask_parking_settings.
            ask_settings=lambda area, data: self._ask_parking_settings(area, data),
            parent=self,
        )

        self.reverse_direction_operation = ReverseDirectionOperation(
            context, connection_at=self._get_connection_at, parent=self
        )

        self.marker_operation = MarkerOperation(
            context,
            # Looked up on each call, so tests can replace _ask_marker.
            ask_marker=lambda *args: self._ask_marker(*args),
            parent=self,
        )

        self.network_check_operation = NetworkCheckOperation(
            context, map_scale=lambda: self.background_map.map_scale, parent=self
        )

        self.edit_operations = [
            self.move_nodes_operation,
            self.delete_nodes_operation,
            self.connect_nodes_operation,
            self.rotate_selection_operation,
            self.create_nodes_operation,
            self.node_type_operation,
            self.align_nodes_operation,
            self.create_path_operation,
            self.clipboard_operation,
            self.node_position_operation,
            self.parking_spot_operation,
            self.reverse_direction_operation,
            self.marker_operation,
            self.network_check_operation,
        ]

    def _create_project_coordinator(self):
        self.project_coordinator = ProjectCoordinator(
            scene=self.scene,
            view=self.view,
            project_files=self.project_files,
            background_map=self.background_map,
            heightmap=self.heightmap,
            scene_renderer=self.scene_renderer,
            selection_coordinator=self.selection_coordinator,
            measurement_coordinator=self.measurement_coordinator,
            map_cache=self.map_cache,
            game_files=self._game_files,
            parent=self,
        )

    def _game_files(self) -> GameFiles:
        installation = self.settings.install_folder
        game_folder = self.settings.game_folder

        return GameFiles(
            installation.path if installation is not None else None,
            game_folder.mods_directory if game_folder is not None else None,
        )

    def _create_file_controllers(self):
        self.files = FileController(
            self,
            self.settings,
            self.project_coordinator,
            self.edit_history,
            AutosaveStore(user_data_directory() / "autosave"),
            self.local_projects_directory,
        )

        self.savegame_link = SavegameLinkController(
            self, self.settings, self.project_coordinator, self.project_files
        )
        self.files.config_opened.connect(self.savegame_link.offer_link)

        self.map_import = MapImportController(
            self, self.settings, self.map_cache, self.project_coordinator
        )

        self.updates = UpdateController(self, self.settings)

    def _register_map_tools(self):
        self.view.register_tool(
            InteractionMode.SELECT, SelectTool(self.view, self.selection_coordinator)
        )

        for interaction_mode, flag in (
            (InteractionMode.CREATE_NODES, REGULAR_FLAG),
            (InteractionMode.CREATE_SUBPRIO_NODES, SUBPRIO_FLAG),
        ):
            self.view.register_tool(
                interaction_mode, CreateNodeTool(self.view, self.create_nodes_operation, flag)
            )

        self.view.register_tool(
            InteractionMode.TOGGLE_NODE_TYPE,
            ToggleNodeTypeTool(self.view, self.node_type_operation),
        )

        self.view.register_tool(
            InteractionMode.REVERSE_DIRECTION,
            NodeClickTool(
                self.view,
                self.reverse_direction_operation.reverse_at,
                tr("Click a connection to reverse its direction"),
                is_target=lambda view_position: self._get_connection_at(view_position) is not None,
            ),
        )

        self.view.register_tool(
            InteractionMode.MOVE_NODES, MoveNodesTool(self.view, self.move_nodes_operation)
        )

        self.view.register_tool(
            InteractionMode.PARKING_SPOTS,
            NodeClickTool(
                self.view,
                self.parking_spot_operation.create_at,
                lambda: (
                    tr("Click a shed to create parking spots in it")
                    if self.scene_renderer.shed_areas
                    else tr("No sheds shown: open a savegame or link one to the route")
                ),
                is_target=lambda view_position: self._get_shed_at(view_position) is not None,
            ),
        )

        self.view.register_tool(
            InteractionMode.EDIT_NODE_POSITION,
            NodeClickTool(
                self.view,
                self.node_position_operation.edit_at,
                tr("Click a node to enter its position"),
            ),
        )

        self.view.register_tool(
            InteractionMode.ROTATE_SELECTION,
            RotateSelectionTool(
                self.view,
                self.rotate_selection_operation,
                z_value=(self.scene_renderer.display_style.selected_node_z + 1),
            ),
        )

        self.view.register_tool(
            InteractionMode.DELETE_NODES, DeleteNodesTool(self.view, self.delete_nodes_operation)
        )

        connect_tools = (
            (InteractionMode.CONNECT_REGULAR, ConnectionType.REGULAR, "regular_connection_color"),
            (InteractionMode.CONNECT_DUAL, ConnectionType.DUAL, "dual_connection_color"),
            (InteractionMode.CONNECT_REVERSE, ConnectionType.REVERSE, "reverse_connection_color"),
        )

        for interaction_mode, connection_type, color_name in connect_tools:
            self.view.register_tool(
                interaction_mode,
                ConnectNodesTool(
                    self.view,
                    self.connect_nodes_operation,
                    connection_type,
                    color_provider=(
                        lambda name=color_name: getattr(self.scene_renderer.display_style, name)
                    ),
                    z_value=(self.scene_renderer.display_style.selected_node_z + 1),
                ),
            )

        self._register_align_tools()

        self._register_path_tools()

        self._register_marker_tools()

        self.view.register_measure_tool(MeasureTool(self.view, self.measurement_coordinator))

    def _register_align_tools(self):
        operation = self.align_nodes_operation
        reference_hint = tr("Select nodes, then click the reference node")

        tools = (
            (InteractionMode.ALIGN_HORIZONTAL, operation.align_horizontal_at, reference_hint),
            (InteractionMode.ALIGN_VERTICAL, operation.align_vertical_at, reference_hint),
            (InteractionMode.ALIGN_HEIGHT, operation.align_height_at, reference_hint),
            (
                InteractionMode.HEIGHT_FROM_TERRAIN,
                operation.height_from_terrain_at,
                tr("Select nodes, then click one of them"),
            ),
        )

        for interaction_mode, click, hint in tools:
            self.view.register_tool(interaction_mode, NodeClickTool(self.view, click, hint))

    def _register_path_tools(self):
        display_style = self.scene_renderer.display_style

        for interaction_mode, shape in (
            (InteractionMode.DRAW_LINE, PathShape.LINE),
            (InteractionMode.DRAW_BEZIER, PathShape.BEZIER),
            (InteractionMode.DRAW_ARC, PathShape.ARC),
        ):
            self.view.register_tool(
                interaction_mode,
                PathTool(
                    self.view,
                    self.create_path_operation,
                    shape,
                    color_provider=(
                        lambda connection_type: getattr(
                            self.scene_renderer.display_style,
                            f"{connection_type.value}_connection_color",
                        )
                    ),
                    node_diameter=display_style.node_diameter,
                    z_value=display_style.selected_node_z + 1,
                ),
            )

    def _create_tool_options(self):
        """The options behind the arrows of the Rotate and path tool buttons."""

        tool_panel = self.actions.tool_panel
        tool_actions = self.actions.tool_actions

        rotate_options = RotateOptionsWidget(self.rotate_selection_operation.snap_angle)

        def apply_snap_angle(angle):
            self.rotate_selection_operation.snap_angle = angle
            self.settings.set_rotate_snap_angle(angle)

        rotate_options.snap_angle_changed.connect(apply_snap_angle)
        tool_panel.set_tool_options(tool_actions[InteractionMode.ROTATE_SELECTION], rotate_options)

        # One options widget per path tool; changing one updates the others.
        self.path_options_widgets = {}

        for interaction_mode, shape in (
            (InteractionMode.DRAW_LINE, PathShape.LINE),
            (InteractionMode.DRAW_BEZIER, PathShape.BEZIER),
            (InteractionMode.DRAW_ARC, PathShape.ARC),
        ):
            widget = PathOptionsWidget(
                self.create_path_operation.options,
                show_control_points=shape == PathShape.BEZIER,
            )
            menu = tool_panel.set_tool_options(tool_actions[interaction_mode], widget)

            widget.options_changed.connect(self._apply_path_options)
            widget.apply_requested.connect(self.create_path_operation.apply)
            widget.apply_requested.connect(menu.close)

            self.path_options_widgets[shape] = widget

        def update_apply_buttons():
            for widget in self.path_options_widgets.values():
                widget.apply_button.setEnabled(self.create_path_operation.is_adjusting)

        self.create_path_operation.preview_changed.connect(update_apply_buttons)

        update_apply_buttons()

    def _apply_path_options(self, options):
        self.create_path_operation.set_options(options)
        self.settings.set_path_options(options)

        for widget in self.path_options_widgets.values():
            widget.blockSignals(True)
            widget.set_options(options)
            widget.blockSignals(False)

    def _register_marker_tools(self):
        operation = self.marker_operation

        def move_hint():
            if operation.move_source_id is None:
                return tr("Click a node with a marker to pick up the marker")

            return tr("Click the target node (right-click or Esc cancels)")

        tools = (
            (
                InteractionMode.ADD_MARKER,
                operation.add_at,
                tr("Click a node without a marker"),
                None,
            ),
            (
                InteractionMode.EDIT_MARKER,
                operation.edit_at,
                tr("Click a node with a marker"),
                None,
            ),
            (InteractionMode.MOVE_MARKER, operation.move_click, move_hint, operation.cancel_move),
            (
                InteractionMode.DELETE_MARKER,
                operation.delete_at,
                tr("Click a node with a marker"),
                None,
            ),
        )

        for interaction_mode, click, hint, cancel in tools:
            self.view.register_tool(
                interaction_mode, NodeClickTool(self.view, click, hint, cancel=cancel)
            )

    def _create_grid_coordinator(self):
        self.grid_coordinator = GridCoordinator(
            background_map=self.background_map,
            grid_controls=self.actions.grid_controls,
            parent=self,
        )

    def _create_debug_dock_coordinator(self):
        self.debug_dock_coordinator = DebugDockCoordinator(
            debug_dock=self.debug_dock,
            view=self.view,
            scene_renderer=self.scene_renderer,
            parent=self,
        )

        self.selection_coordinator.selection_state_changed.connect(
            self.debug_dock_coordinator.refresh
        )

        self.project_coordinator.debug_refresh_requested.connect(
            self.debug_dock_coordinator.refresh
        )

    def _get_terrain_height(self, x: float, z: float) -> float | None:
        """Terrain height from the loaded heightmap, or None without
        heightmap or outside the map."""

        if not self.heightmap.has_heightmap():
            return None

        try:
            return self.heightmap.get_height_at(
                world_x=x, world_z=z, map_scale=self.background_map.map_scale
            ).height

        except ValueError:
            return None

    def _get_paste_position(self) -> tuple[float, float]:
        """Scene position of the mouse, or the view center if the mouse
        is outside the map."""

        viewport = self.view.viewport()
        view_position = viewport.mapFromGlobal(QCursor.pos())

        if not viewport.rect().contains(view_position):
            view_position = viewport.rect().center()

        scene_position = self.view.mapToScene(view_position)

        return scene_position.x(), scene_position.y()

    def _get_shed_at(self, view_position):
        scene_position = self.view.mapToScene(view_position)

        return self.scene_renderer.get_shed_at(scene_position.x(), scene_position.y())

    def _get_connection_at(self, view_position):
        scene_position = self.view.mapToScene(view_position)

        return self.scene_renderer.get_connection_at(
            scene_position.x(),
            scene_position.y(),
            tolerance=self.CONNECTION_CLICK_TOLERANCE / self.view.zoom_level,
        )

    def _get_autodrive_data(self) -> AutoDriveData | None:
        return self.project_coordinator.autodrive_data

    def _create_status_widgets(self):
        self.status = QLabel(self.NO_FILE_STATUS)

        self.statusBar().addWidget(self.status, 1)

    def _create_central_widget(self):
        self.setCentralWidget(self.view)

    def _create_welcome_panel(self):
        self.welcome_panel = WelcomePanel(
            [
                self.actions.open_route_action,
                self.actions.open_savegame_action,
                self.actions.load_xml_action,
            ],
            self.view.viewport(),
        )

        layout = QVBoxLayout(self.view.viewport())
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.welcome_panel)

        self.welcome_panel.set_recent_items(self.settings.recent_items)
        self.welcome_panel.recent_item_requested.connect(self.files.open_recent)
        self.files.recent_items_changed.connect(self.welcome_panel.set_recent_items)

    def _create_marker_dock(self):
        self.marker_dock = MarkerDock(self)

        self.addDockWidget(Qt.RightDockWidgetArea, self.marker_dock)

        self.marker_dock.marker_activated.connect(self.focus_marker)
        self.marker_dock.edit_requested.connect(self.marker_operation.edit_marker)
        self.marker_dock.rename_group_requested.connect(self.rename_marker_group)
        self.marker_dock.delete_group_requested.connect(self.marker_operation.delete_group)

    def _create_check_dock(self):
        self.check_dock = CheckDock(*self.settings.check_tolerances, parent=self)

        self.addDockWidget(Qt.RightDockWidgetArea, self.check_dock)

        self.check_dock.hide()

        self.check_dock.nodes_activated.connect(self.focus_nodes)

        def network_path():
            source = self.project_coordinator.config_source
            return source.path if source is not None else None

        self.network_check = NetworkCheckController(
            self.check_dock,
            self.network_check_operation,
            self.settings,
            IgnoreStore(user_data_directory() / "check_ignores.json"),
            autodrive_data=self._get_autodrive_data,
            network_path=network_path,
            map_scale=lambda: self.background_map.map_scale,
            terrain_height_at=lambda: (
                self._get_terrain_height if self.heightmap.has_heightmap() else None
            ),
            parent=self,
        )

    def _create_debug_dock(self):
        self.debug_dock = DebugDock(self)

        self.addDockWidget(Qt.RightDockWidgetArea, self.debug_dock)

        self.debug_dock.set_node_info(self.NO_SELECTION_INFO)

        self.debug_dock.hide()

    def _connect_signals(self):
        self.view.rotation_changed.connect(self._handle_rotation_changed)

        self.measurement_coordinator.status_changed.connect(self._set_status)

        self.measurement_coordinator.measurement_mode_changed.connect(
            self.actions.set_measurement_mode
        )

        self.measurement_coordinator.alignment_available_changed.connect(
            self.actions.set_measurement_alignment_enabled
        )

        self.selection_coordinator.selection_info_changed.connect(self.debug_dock.set_node_info)

        self.project_coordinator.status_changed.connect(self._set_status)

        self.grid_coordinator.status_changed.connect(self._set_status)

        self.project_coordinator.map_scale_changed.connect(self._handle_map_scale_changed)

        self.project_coordinator.heightmap_path_changed.connect(self._handle_heightmap_path_changed)

        self.project_coordinator.autodrive_data_loaded.connect(self._handle_autodrive_data_loaded)

        self.project_coordinator.map_missing.connect(self.map_import.offer_missing_map)

        self.edit_history.clean_changed.connect(self._handle_edit_clean_changed)

        self.edit_history.data_changed.connect(self._handle_data_changed)

        self.files.status_changed.connect(self._set_status)

        self.files.saved.connect(self._update_window_title)
        self.savegame_link.status_changed.connect(self._set_status)

        self.map_import.status_changed.connect(self._set_status)

        for operation in self.edit_operations:
            operation.status_changed.connect(self._set_status)

        # Keeps the tool buttons right even when the mode is changed
        # without clicking a button.
        self.view.interaction_mode_changed.connect(
            lambda interaction_mode: self.actions.sync_tool_actions()
        )

        self.node_selection.selection_changed.connect(
            lambda node_ids, primary_node_id: self.actions.delete_selection_action.setEnabled(
                bool(node_ids)
            )
        )

        self.view.rotation_step_changed.connect(self._handle_rotation_step_changed)

    def _handle_rotation_changed(self, rotation_angle: float):
        rotation_active = (
            abs(rotation_angle) >= ViewRotationController.ROTATION_COMPARISON_TOLERANCE
        )

        self.actions.reset_rotation_action.setEnabled(rotation_active)

        self.actions.rotation_controls.set_rotation_angle(rotation_angle)

    def _handle_rotation_step_changed(self, rotation_step: float):
        self.actions.rotation_controls.set_rotation_step(rotation_step)

    def _handle_heightmap_path_changed(self, file_path):
        self.actions.remove_heightmap_action.setEnabled(file_path is not None)

    def _handle_map_scale_changed(self, map_scale: int):
        self.actions.set_current_map_scale(map_scale)

    def _handle_autodrive_data_loaded(self, autodrive_data):
        # Edits of the previous data cannot be undone on new data.
        self.edit_history.clear()

        self.connect_nodes_operation.end_chain()

        self.marker_operation.reset_move()

        self.create_path_operation.reset()

        self.marker_dock.set_data(autodrive_data)

        self.network_check.network_loaded()

        self.welcome_panel.hide()

        self.setWindowModified(False)
        self.actions.save_xml_action.setEnabled(True)
        self.actions.save_xml_as_action.setEnabled(True)
        source = self.project_coordinator.config_source
        self.actions.link_savegame_action.setEnabled(
            source is not None and source.format == ConfigFormat.ROUTE_EXPORT
        )

        self._update_window_title()

    def _update_window_title(self):
        source = self.project_coordinator.config_source

        if source is not None:
            self.setWindowTitle(
                f"{self.WINDOW_TITLE} – {source.display_name} ({source.format_label})[*]"
            )

    def _handle_data_changed(self, data_change: DataChange):
        self.scene_renderer.apply_changes(
            moved_node_ids=data_change.moved_node_ids,
            added_node_ids=data_change.added_node_ids,
            removed_node_ids=data_change.removed_node_ids,
            connection_node_ids=data_change.connection_node_ids,
            changed_flag_node_ids=data_change.changed_flag_node_ids,
            changed_marker_node_ids=data_change.changed_marker_node_ids,
        )

        if data_change.affects_markers:
            self.marker_dock.set_data(self._get_autodrive_data())

        if data_change.removed_node_ids:
            self.node_selection.remove(data_change.removed_node_ids)

        # Node coordinates in the info panel may have changed.
        self.selection_coordinator.refresh_info()

    def _handle_edit_clean_changed(self, clean: bool):
        self.setWindowModified(not clean)

    def _set_status(self, message: str):
        self.status.setText(message)
