from collections.abc import Callable

from PySide6.QtCore import QEventLoop, QObject, Qt, QTimer, Signal
from PySide6.QtWidgets import QApplication, QDialog, QWidget

from autodrive_editor.editing.operations.bunker_silos import BunkerSiloOperation
from autodrive_editor.editing.operations.find_route import FindRouteOperation
from autodrive_editor.editing.operations.junction import JunctionOperation
from autodrive_editor.editing.operations.move_nodes import MoveNodesOperation
from autodrive_editor.editing.operations.parking_spots import (
    MIXED_TYPES_TEXT,
    ParkingSpotOperation,
)
from autodrive_editor.editing.operations.road_network import RoadMode, RoadNetworkOperation
from autodrive_editor.editing.operations.stations import StationOperation
from autodrive_editor.file_io.game_files import GameFiles
from autodrive_editor.file_io.traffic_splines import map_traffic_lanes
from autodrive_editor.i18n import tr
from autodrive_editor.project.project_coordinator import ProjectCoordinator
from autodrive_editor.rendering.scene_renderer import SceneRenderer
from autodrive_editor.selection.selection_coordinator import SelectionCoordinator
from autodrive_editor.settings.app_settings import AppSettings
from autodrive_editor.ui.dialogs.parking_map_overlay import ParkingMapOverlay
from autodrive_editor.ui.dialogs.parking_spot_dialog import ParkingSpotDialog
from autodrive_editor.ui.dialogs.progress_dialog import GeneratorFailed, run_with_progress
from autodrive_editor.ui.dialogs.silo_dialog import SiloDialog
from autodrive_editor.ui.dialogs.station_dialog import StationDialog
from autodrive_editor.ui.map_view.dialog_placement import place_beside
from autodrive_editor.ui.map_view.map_only_input import MapOnlyInput
from autodrive_editor.ui.map_view.map_view import MapView
from autodrive_editor.ui.panels.generate_options import GenerateOptionsWidget
from autodrive_editor.ui.planning_controller import PlanningController
from autodrive_editor.ui.tools.area_pick_tool import AreaPickTool
from autodrive_editor.ui.tools.find_route_tool import FindRouteTool
from autodrive_editor.ui.tools.generate_tool import GenerateTask, GenerateTool
from autodrive_editor.ui.tools.junction_tool import JunctionTool
from autodrive_editor.ui.tools.lane_handle_tool import LaneHandleTool
from autodrive_editor.ui.tools.map_tool import MapTool
from autodrive_editor.ui.tools.navigate_tool import NavigateTool
from autodrive_editor.ui.tools.roads_tool import RoadsTool
from autodrive_editor.ui.tools.station_pick_tool import StationPickTool


class GeneratorController(QObject):
    """The Generate tool with its task tools, the generator dialogs beside the map, and the
    traffic lanes the Roads task shows."""

    status_changed = Signal(str)

    # How close to a stop arrow or a road a click picks it, in pixels.
    STOP_CLICK_TOLERANCE = 12.0

    def __init__(
        self,
        window: QWidget,
        view: MapView,
        scene_renderer: SceneRenderer,
        selection_coordinator: SelectionCoordinator,
        settings: AppSettings,
        planning: PlanningController,
        project_coordinator: ProjectCoordinator,
        game_files: Callable[[], GameFiles],
        connection_at: Callable,
        *,
        find_route: FindRouteOperation,
        move_nodes: MoveNodesOperation,
        junction: JunctionOperation,
        parking_spots: ParkingSpotOperation,
        bunker_silos: BunkerSiloOperation,
        stations: StationOperation,
        roads: RoadNetworkOperation,
    ):
        super().__init__(window)

        self.window = window
        self.view = view
        self.scene_renderer = scene_renderer
        self.selection_coordinator = selection_coordinator
        self.settings = settings
        self.planning = planning
        self.project_coordinator = project_coordinator
        self.game_files = game_files
        self.connection_at = connection_at
        self.find_route = find_route
        self.junction = junction
        self.roads = roads

        # The Roads task is active, so its traffic lanes are shown.
        self._roads_shown = False

        self._create_tool(move_nodes, parking_spots, bunker_silos, stations)

    def _create_tool(self, move_nodes, parking_spots, bunker_silos, stations):
        display_style = self.scene_renderer.display_style
        renderer = self.scene_renderer
        route_tool = FindRouteTool(
            self.view,
            self.find_route,
            move_nodes,
            node_at=self.selection_coordinator.get_node_at,
            connection_at=self.connection_at,
            color_provider=lambda: renderer.display_style.regular_connection_color,
            z_value=display_style.selected_node_z + 1,
        )
        parking_tool = AreaPickTool(
            self.view,
            self._get_shed_at,
            renderer.get_sheds_in_path,
            parking_spots.create_for,
            self._show_picked_sheds,
            lambda: (
                tr("Click a shed, Shift-click or right-drag a box to pick several of one type")
                if renderer.shown_shed_areas
                else tr("No sheds shown: open a savegame")
            ),
            hover_text=self._get_shed_name_at,
            may_add=self._may_pick_shed,
        )
        station_tool = StationPickTool(
            self.view,
            lambda view_position: stations.create_for(self._get_station_stops_at(view_position)),
            lambda path: stations.create_for(renderer.get_stops_in_path(path)),
            lambda: (
                tr("Click a station or right-drag a box around several to create their lanes")
                if renderer.shown_stops
                else tr("No stations shown: open a savegame")
            ),
            is_target=lambda view_position: bool(self._get_station_stops_at(view_position)),
            hover_text=self._get_station_name_at,
        )
        silo_tool = AreaPickTool(
            self.view,
            self._get_silo_at,
            renderer.get_silos_in_path,
            bunker_silos.create_for,
            self._show_picked_silos,
            lambda: (
                tr("Click a bunker silo, Shift-click or right-drag a box to pick several")
                if renderer.shown_silo_areas
                else tr("No bunker silos shown: open a savegame")
            ),
            hover_text=self._get_silo_name_at,
        )
        junction_tool = JunctionTool(
            self.view,
            self.junction,
            connection_at=self.connection_at,
            node_at=self._get_node_id_at,
            color_provider=lambda: renderer.display_style.regular_connection_color,
            missing_costmap_message=self.find_route.missing_costmap_message,
            z_value=display_style.selected_node_z + 1,
        )
        roads_tool = RoadsTool(
            self.view,
            click=self._create_road_at,
            pick_area=self._create_roads_in,
            create=self._create_roads,
            shown=self._show_roads,
            hint=self._roads_hint,
            is_target=lambda view_position: self._road_at(view_position) is not None,
        )
        self.tool = GenerateTool(
            self.view,
            {
                GenerateTask.ROUTE: route_tool,
                GenerateTask.JUNCTION: junction_tool,
                GenerateTask.PARKING_SPOTS: parking_tool,
                GenerateTask.STATIONS: station_tool,
                GenerateTask.BUNKER_SILOS: silo_tool,
                GenerateTask.ROADS: roads_tool,
            },
            start_planning=lambda: self.planning.start_plan(),
        )

    def create_options(self, actions):
        """The Generate tool's options bar widget, with the task buttons of the actions."""

        self.actions = actions
        self.options = GenerateOptionsWidget(
            actions.generate_task_actions,
            self.tool.task,
            *self.settings.junction_stem,
            self.settings.junction_style,
            self.roads.settings,
        )
        actions.show_generate_task(self.tool.task)
        self.options.stem_changed.connect(self.settings.set_junction_stem)
        self.options.style_changed.connect(self.settings.set_junction_style)
        self.options.remove_last_requested.connect(self.find_route.remove_last)
        self.options.clear_requested.connect(self.find_route.clear)
        self.options.road_settings_changed.connect(
            lambda settings: setattr(self.roads, "settings", settings)
        )
        self.options.create_roads_requested.connect(self._create_roads)

        return self.options

    def set_task(self, task: GenerateTask):
        """Picks what the Generate tool creates."""

        self.tool.set_task(task)
        self.actions.show_generate_task(task)
        self.options.set_task(task)

    def network_loaded(self):
        """Another savegame may have another map: its lanes are read when Roads needs them."""

        self.roads.forget()
        self.scene_renderer.set_traffic_lanes([])
        self._show_roads(self._roads_shown)

    def ask_parking_settings(self, areas, autodrive_data):
        taken_names = {(marker.name, marker.group) for marker in autodrive_data.markers.values()}
        dialog = ParkingSpotDialog(
            areas,
            autodrive_data.marker_group_names(),
            taken_names,
            self.settings,
            parent=self.window,
        )

        return self._run_area_dialog(dialog, areas)

    def ask_silo_settings(self, areas, autodrive_data):
        taken_names = {(marker.name, marker.group) for marker in autodrive_data.markers.values()}
        dialog = SiloDialog(
            areas,
            self.scene_renderer.costmap,
            autodrive_data.marker_group_names(),
            taken_names,
            self.settings,
            parent=self.window,
        )

        return self._run_area_dialog(dialog, areas)

    def _run_area_dialog(self, dialog, areas):
        """Runs a shed or silo dialog beside the areas, with its plan on the map."""

        overlay = ParkingMapOverlay(self.scene_renderer.display_style)

        def show(piece):
            overlay.set_network(piece, [] if piece is None else [p[::2] for p in piece.points])

        show(dialog.area_plan)
        dialog.area_plan_changed.connect(show)
        self.view.scene().addItem(overlay)
        place_beside(dialog, self.view, [corner for area in areas for corner in area.corners])

        try:
            accepted = self._run_beside_map(dialog)
        finally:
            self.view.scene().removeItem(overlay)

        return dialog.settings if accepted else None

    def ask_station_choices(self, stops, autodrive_data):
        taken_names = {(marker.name, marker.group) for marker in autodrive_data.markers.values()}
        headings = self.scene_renderer.stop_headings
        dialog = StationDialog(
            stops,
            [headings.get(stop, stop.heading) for stop in stops],
            taken_names,
            autodrive_data,
            self.settings,
            parent=self.window,
        )
        overlay = ParkingMapOverlay(self.scene_renderer.display_style)
        dialog.plan_changed.connect(overlay.set_network)
        dialog.plan_changed.connect(
            lambda *_: overlay.set_handles([(x, z) for _, _, x, z in dialog.handles()])
        )
        dialog._update()
        self.view.scene().addItem(overlay)
        handle_tool = LaneHandleTool(
            self.view,
            dialog.handles,
            dialog.drag_handle,
            self.selection_coordinator.get_node_at,
            drawing=dialog,
        )

        place_beside(dialog, self.view, [stop.position[::2] for stop in stops])

        try:
            # Enter and Esc on the map finish drawing the yard road.
            keys = {Qt.Key_Return, Qt.Key_Enter, Qt.Key_Escape}
            accepted = self._run_beside_map(dialog, handle_tool, keys)
        finally:
            self.view.scene().removeItem(overlay)

        return (dialog.lane_choices, dialog.settings, dialog.yard) if accepted else None

    def _run_beside_map(self, dialog: QDialog, tool: MapTool | None = None, map_keys=()) -> bool:
        """Runs the dialog without blocking the map: it can be moved, zoomed and rotated, but
        nothing else in the window reacts until the dialog is closed. tool, if given, handles
        the mouse on the map instead of plain navigation, and the keys in map_keys."""

        loop = QEventLoop()
        dialog.finished.connect(loop.quit)
        input_filter = MapOnlyInput(self.window, self.view, map_keys)
        QApplication.instance().installEventFilter(input_filter)
        self.view.set_override_tool(tool or NavigateTool(self.view))

        try:
            dialog.show()
            loop.exec()
        finally:
            QApplication.instance().removeEventFilter(input_filter)
            self.view.set_override_tool(None)

        return dialog.result() == QDialog.DialogCode.Accepted

    def read_traffic_lanes(self, savegame):
        cache = self.project_coordinator.building_cache

        with self.game_files() as files:
            lanes = map_traffic_lanes(savegame, files, cache)

        cache.save()
        return lanes

    def run_generator(self, title: str, work):
        """Runs the work with the progress dialog: its result, or None after Cancel or a
        failure (the status says so)."""

        try:
            return run_with_progress(title, work, self.window)
        except GeneratorFailed:
            self.status_changed.emit(tr("The generator failed. Details are in the log file"))
            return None

    def _show_roads(self, shown: bool):
        self._roads_shown = shown

        if not shown:
            self.scene_renderer.set_traffic_lanes([])
            return

        # After the tool change: reading the lanes may show the progress dialog.
        QTimer.singleShot(0, self._prepare_roads)

    def _prepare_roads(self):
        if self._roads_shown:
            self.roads.prepare()
            self.scene_renderer.set_traffic_lanes(self.roads.lanes)

    def _create_roads(self) -> bool:
        """Builds the roads of the whole map into the plan, in the Whole map mode."""

        return self._build_roads(RoadMode.WHOLE_MAP, self.roads.create)

    def _create_roads_in(self, path) -> bool:
        """Builds the roads in the dragged box or lasso, in the Box mode."""

        box = [(point.x(), point.y()) for point in path.toFillPolygon()]

        return self._build_roads(RoadMode.BOX, lambda: self.roads.create_in_box(box))

    def _road_at(self, view_position) -> int | None:
        """The road under the pointer, in the Click road mode."""

        if self.roads.settings.mode != RoadMode.CLICK_ROAD:
            return None

        position = self.view.mapToScene(view_position)
        reach = self.STOP_CLICK_TOLERANCE / self.view.zoom_level

        return self.roads.road_at(position.x(), position.y(), reach)

    def _create_road_at(self, view_position) -> bool:
        position = self.view.mapToScene(view_position)
        reach = self.STOP_CLICK_TOLERANCE / self.view.zoom_level

        return self._build_roads(
            RoadMode.CLICK_ROAD, lambda: self.roads.create_at(position.x(), position.y(), reach)
        )

    def _build_roads(self, mode: RoadMode, create) -> bool:
        operation = self.roads

        if operation.settings.mode != mode or not operation.prepare():
            return False

        self.scene_renderer.set_traffic_lanes(operation.lanes)
        self.planning.start_plan()
        return create()

    def _roads_hint(self) -> str:
        if not self.roads.lanes:
            return tr(
                "Roads are built from the map's traffic lanes: open a savegame of a map with them"
            )

        return {
            RoadMode.BOX: tr("Right-drag a box around the roads to build"),
            RoadMode.WHOLE_MAP: tr("Enter or Create builds the roads of the whole map"),
            RoadMode.CLICK_ROAD: tr("Click a road to build it from junction to junction"),
        }[self.roads.settings.mode]

    def _get_shed_at(self, view_position):
        scene_position = self.view.mapToScene(view_position)

        return self.scene_renderer.get_shed_at(scene_position.x(), scene_position.y())

    def _get_shed_name_at(self, view_position) -> str:
        area = self._get_shed_at(view_position)

        return f"{area.name} – {area.category_label}" if area is not None else ""

    def _show_picked_sheds(self, areas):
        self.scene_renderer.set_picked_sheds(areas)

        if len(areas) > 1:
            self.status_changed.emit(
                tr(
                    "{count} sheds picked: Enter or a click on one of them creates their parking "
                    "spots, Esc drops the pick",
                    count=len(areas),
                )
            )

    def _may_pick_shed(self, picked, area) -> bool:
        if picked and area.building_file != picked[0].building_file:
            self.status_changed.emit(MIXED_TYPES_TEXT)
            return False

        return True

    def _get_silo_at(self, view_position):
        scene_position = self.view.mapToScene(view_position)

        return self.scene_renderer.get_silo_at(scene_position.x(), scene_position.y())

    def _get_silo_name_at(self, view_position) -> str:
        area = self._get_silo_at(view_position)

        return area.name if area is not None else ""

    def _show_picked_silos(self, areas):
        self.scene_renderer.set_picked_silos(areas)

        if len(areas) > 1:
            self.status_changed.emit(
                tr(
                    "{count} bunker silos picked: Enter or a click on one of them creates their "
                    "lanes, Esc drops the pick",
                    count=len(areas),
                )
            )

    def _get_station_stops_at(self, view_position):
        scene_position = self.view.mapToScene(view_position)
        tolerance = self.STOP_CLICK_TOLERANCE / self.view.zoom_level

        return self.scene_renderer.get_station_stops_at(
            scene_position.x(), scene_position.y(), tolerance
        )

    def _get_station_name_at(self, view_position) -> str:
        names = dict.fromkeys(
            stop.name.strip() for stop in self._get_station_stops_at(view_position)
        )

        return ", ".join(names)

    def _get_node_id_at(self, view_position) -> int | None:
        node = self.selection_coordinator.get_node_at(view_position)

        return None if node is None else node.node_id
