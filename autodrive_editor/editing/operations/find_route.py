import logging
import threading
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import Signal

from autodrive_editor.editing.commands.add_route import AddRouteCommand
from autodrive_editor.editing.edit_context import EditContext, EditOperation
from autodrive_editor.editing.route_finder import RouteFinder, RouteRequest, Vehicle
from autodrive_editor.editing.route_nodes import (
    chain_connections,
    node_headings,
    planned_lanes,
    route_nodes,
)
from autodrive_editor.file_io.navigation_costmap import NavigationCostmap
from autodrive_editor.i18n import tr
from autodrive_editor.model.autodrive_data import AutoDriveData, NodeData
from autodrive_editor.model.connections import CONNECTION_STATES, ConnectionType

logger = logging.getLogger(__name__)


class FindRouteOperation(EditOperation):
    """Find route: a drivable route from one selected node to the other, the one clicked last.
    The search runs in a background thread; the route is added to the plan as one undo step."""

    # A search started or ended.
    searching_changed = Signal(bool)
    # From the search thread: the points of the route or None.
    _search_done = Signal(object)

    def __init__(
        self,
        context: EditContext,
        costmap_provider: Callable[[], NavigationCostmap | None],
        savegame_provider: Callable[[], Path | None],
        vehicle_provider: Callable[[], Vehicle],
        spacing_provider: Callable[[], float],
        plan_node_ids_provider: Callable[[], set[int]],
        height_for_new_node: Callable[[AutoDriveData, float, float], float],
        parent=None,
    ):
        super().__init__(context, parent)

        self.costmap_provider = costmap_provider
        self.savegame_provider = savegame_provider
        self.vehicle_provider = vehicle_provider
        self.spacing_provider = spacing_provider
        self.plan_node_ids_provider = plan_node_ids_provider
        self.height_for_new_node = height_for_new_node

        self._search: dict | None = None
        self._search_done.connect(self._finish)
        self.edit_history.data_changed.connect(self._handle_data_changed)

    @property
    def is_searching(self) -> bool:
        return self._search is not None

    def find_route(self) -> bool:
        """Starts the search. Returns False with a message if it cannot start."""

        autodrive_data = self.autodrive_data_provider()

        if autodrive_data is None or self.is_searching or self.edit_history.history_locked:
            return False

        if not self.edit_history.is_planning:
            self.status_changed.emit(tr("Find route works in planning mode"))
            return False

        costmap = self.costmap_provider()

        if costmap is None:
            self.status_changed.emit(self._missing_costmap_message())
            return False

        selected = self.node_selection.selected_node_ids

        if len(selected) != 2:
            self.status_changed.emit(tr("Select the two nodes the route should connect"))
            return False

        goal_id = self.node_selection.primary_node_id
        (start_id,) = selected - {goal_id}
        start, goal = autodrive_data.nodes[start_id], autodrive_data.nodes[goal_id]

        lanes = planned_lanes(autodrive_data, self.plan_node_ids_provider())
        request = RouteRequest(
            (start.x, start.z),
            (goal.x, goal.z),
            node_headings(autodrive_data, start_id),
            node_headings(autodrive_data, goal_id),
            tuple((lane.source, lane.target) for lane in lanes),
        )
        cancelled = threading.Event()
        self._search = {
            "data": autodrive_data,
            "start_id": start_id,
            "goal_id": goal_id,
            "lanes": lanes,
            "cancelled": cancelled,
        }
        vehicle = self.vehicle_provider()
        self._search["vehicle"] = vehicle
        logger.debug(
            "Find route from node %d to node %d, %d planned nodes",
            start_id,
            goal_id,
            len(self.plan_node_ids_provider()),
        )
        finder = RouteFinder(costmap, vehicle)

        def search():
            self._search_done.emit(finder.find(request, cancelled.is_set))

        threading.Thread(target=search, daemon=True).start()

        self.status_changed.emit(
            tr("Finding a route from node {start} to node {goal}…", start=start_id, goal=goal_id)
        )
        self.searching_changed.emit(True)

        return True

    def cancel(self):
        """Stops a running search; its result is dropped."""

        if self._search is not None:
            self._search["cancelled"].set()

    def _handle_data_changed(self, _data_change):
        # The route would be built on nodes that may have moved or gone.
        self.cancel()

    def _finish(self, points):
        search, self._search = self._search, None
        self.searching_changed.emit(False)

        if search is None:
            return

        if (
            search["cancelled"].is_set()
            or search["data"] is not self.autodrive_data_provider()
            or not self.edit_history.is_planning
        ):
            logger.debug("Route search result dropped: the network or the plan changed")
            self.status_changed.emit(
                tr("Route search stopped, because the network or the plan changed")
            )
            return

        if points is None:
            self.status_changed.emit(
                tr(
                    "No drivable route found from node {start} to node {goal}",
                    start=search["start_id"],
                    goal=search["goal_id"],
                )
            )
            return

        count = self._add_route(search, points)
        self.status_changed.emit(tr("Route with {count} new nodes found", count=count))

    def _add_route(self, search: dict, points) -> int:
        """Adds the route as one undo step. Returns the number of new nodes."""

        autodrive_data = search["data"]
        start_id, goal_id = search["start_id"], search["goal_id"]
        lanes = search["lanes"]

        positions = {
            node_id: (node.x, node.z)
            for node_id in {start_id, goal_id}
            | {lane.source_id for lane in lanes}
            | {lane.target_id for lane in lanes}
            if (node := autodrive_data.nodes.get(node_id)) is not None
        }
        vehicle = search["vehicle"]
        chain = route_nodes(
            points,
            start_id,
            goal_id,
            positions,
            lanes,
            self.spacing_provider(),
            vehicle.width + vehicle.margin,
        )

        next_id = max(autodrive_data.nodes, default=0) + 1
        new_nodes = []
        node_ids = []

        for item in chain:
            if isinstance(item, int):
                node_ids.append(item)
                continue

            x, z = item
            y = self.height_for_new_node(autodrive_data, x, z)
            new_nodes.append(NodeData(next_id, x, y, z))
            node_ids.append(next_id)
            next_id += 1

        connections = chain_connections(autodrive_data, node_ids)
        dual = CONNECTION_STATES[ConnectionType.DUAL]
        logger.debug(
            "Route of %d points: %d new nodes, existing nodes used %s, made dual %s",
            len(points),
            len(new_nodes),
            [item for item in chain if isinstance(item, int)],
            [(source, target) for source, target, state in connections if state == dual],
        )

        self.edit_history.push(
            AddRouteCommand(tr("Find route"), autodrive_data, new_nodes, connections)
        )

        return len(new_nodes)

    def _missing_costmap_message(self) -> str:
        if self.savegame_provider() is None:
            return tr("Find route needs the drivability map of a savegame. Link a savegame first")

        return tr(
            "The savegame has no drivability map yet. Save the game in Farming Simulator first "
            "(again after placing buildings)"
        )
