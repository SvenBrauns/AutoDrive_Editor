from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from PySide6.QtCore import Signal

from autodrive_editor.editing.edit_context import EditContext, EditOperation
from autodrive_editor.editing.planned_piece import push_piece
from autodrive_editor.editing.road_check import check_road_network
from autodrive_editor.editing.road_existing import fit_to_existing, mostly_two_way
from autodrive_editor.editing.road_graph import RoadGraph, build_road_graph
from autodrive_editor.editing.road_network import RoadOptions, build_road_network
from autodrive_editor.file_io.navigation_costmap import NavigationCostmap
from autodrive_editor.file_io.traffic_splines import TrafficLane
from autodrive_editor.i18n import tr

# work(report(done, total, text), cancelled()) → result
Work = Callable[[Callable[[int, int, str], None], Callable[[], bool]], object]
# Runs the work with a progress dialog: its result, or None after Cancel or a failure.
Run = Callable[[str, Work], object]


class RoadMode(Enum):
    BOX = "box"
    WHOLE_MAP = "whole_map"
    CLICK_ROAD = "click_road"


class RoadLanes(Enum):
    AUTO = "auto"  # as most of the existing network
    PAIRS = "pairs"  # two one-way lanes
    TWO_WAY = "two_way"  # one two-way lane


@dataclass(frozen=True)
class RoadSettings:
    mode: RoadMode = RoadMode.WHOLE_MAP
    replace: bool = False  # replace existing roads, else skip them and connect
    lanes: RoadLanes = RoadLanes.AUTO


class RoadNetworkOperation(EditOperation):
    """Builds AutoDrive roads from the traffic lanes of the savegame's map (see road_network),
    fitted to the existing network and checked, in one undo step."""

    # The places to look at of the last run: (point, text).
    places_found = Signal(list)

    def __init__(
        self,
        context: EditContext,
        savegame_provider: Callable[[], Path | None],
        read_lanes: Callable[[Path], list[TrafficLane]],
        costmap_provider: Callable[[], NavigationCostmap | None],
        gap_provider: Callable[[], float],
        run: Run,
        parent=None,
    ):
        super().__init__(context, parent)

        self.savegame_provider = savegame_provider
        self.read_lanes = read_lanes
        self.costmap_provider = costmap_provider
        self.gap_provider = gap_provider
        self.run = run
        self.settings = RoadSettings()
        self.lanes: list[TrafficLane] = []
        self.graph: RoadGraph | None = None
        self._savegame: Path | None = None

    def forget(self):
        """Drops the read lanes, e.g. when another file was opened."""

        self._savegame, self.lanes, self.graph = None, [], None

    def prepare(self) -> bool:
        """Reads the traffic lanes of the loaded savegame's map unless already read. False if
        there are none to build roads from (the status says why)."""

        savegame = self.savegame_provider()

        if savegame is None:
            self.status_changed.emit(
                tr("Roads are built from the map's traffic lanes: open a savegame")
            )
            return False

        if savegame != self._savegame:

            def work(report, cancelled):
                report(0, 2, tr("Reading the map's traffic lanes…"))
                lanes = self.read_lanes(savegame)

                if cancelled():
                    return None

                report(1, 2, tr("Finding roads and junctions…"))
                return lanes, build_road_graph(lanes)

            result = self.run(tr("Roads"), work)

            if result is None:
                return False

            self._savegame = savegame
            self.lanes, self.graph = result

        if not self.lanes:
            self.status_changed.emit(
                tr("This map has no traffic lanes, so roads cannot be generated here")
            )
            return False

        if all(junction.crossing for junction in self.graph.junctions):
            self.status_changed.emit(
                tr(
                    "This map's traffic lanes are only a few loops without junctions: check the "
                    "roads where they cross"
                )
            )

        return True

    def create(self) -> bool:
        """Builds the roads of the whole map into the plan."""

        autodrive_data = self.autodrive_data_provider()

        if autodrive_data is None or self.edit_history.history_locked or self.graph is None:
            return False

        graph, settings = self.graph, self.settings
        gap, costmap = self.gap_provider(), self.costmap_provider()
        two_way = {
            RoadLanes.AUTO: mostly_two_way(autodrive_data),
            RoadLanes.PAIRS: False,
            RoadLanes.TWO_WAY: True,
        }[settings.lanes]

        def work(report, cancelled):
            report(0, 3, tr("Building the roads…"))
            network = build_road_network(graph, RoadOptions(gap=gap, two_way=two_way))

            if cancelled():
                return None

            report(1, 3, tr("Fitting them to the existing network…"))
            network = fit_to_existing(network, autodrive_data, settings.replace, gap)

            if cancelled():
                return None

            report(2, 3, tr("Checking the roads…"))
            return check_road_network(network, graph, autodrive_data, costmap)

        network = self.run(tr("Roads"), work)

        if network is None:
            return False

        self.places_found.emit(network.listed)
        piece = network.piece

        if not piece.points and not piece.removed:
            self.status_changed.emit(tr("No roads to add: the network already has them"))
            return False

        push_piece(self.edit_history, autodrive_data, piece, tr("Create roads"))
        self.status_changed.emit(
            tr(
                "Roads created with {count} nodes; {places} places to look at are listed in the "
                "network check",
                count=len(piece.points),
                places=len(network.listed),
            )
            if network.listed
            else tr("Roads created with {count} nodes", count=len(piece.points))
        )

        return True
