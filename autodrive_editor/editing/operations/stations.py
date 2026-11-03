from collections.abc import Callable

from PySide6.QtCore import Signal

from autodrive_editor.editing.edit_context import EditContext, EditOperation
from autodrive_editor.editing.route_finder import CURVE_RADIUS, RouteFinder, Vehicle
from autodrive_editor.editing.station_join import direct_command, plan_direct
from autodrive_editor.editing.station_layout import StationSettings, StopChoice
from autodrive_editor.file_io.navigation_costmap import NavigationCostmap
from autodrive_editor.file_io.savegame_stations import Stop
from autodrive_editor.i18n import tr
from autodrive_editor.model.autodrive_data import AutoDriveData

# Asks which stops to build and how; None if cancelled.
ChoiceRequest = Callable[
    [list[Stop], AutoDriveData], tuple[list[StopChoice], StationSettings] | None
]
# Runs work(report, cancelled) under a title and returns its result, None if cancelled.
GeneratorRunner = Callable[[str, Callable], object]


def run_directly(title: str, work: Callable) -> object:
    return work(lambda *_: None, lambda: False)


class StationOperation(EditOperation):
    """Creates the lanes and markers of picked station stops, each lane joined straight to the
    nearest road (see station_join), in one undo step. The legs are built in run_generator (the
    progress dialog), with the route finder where curves do not fit. The lane ends still
    without a way in or out are selected, the stops passed to show_missing and the legs that do
    not fit sent with gaps_changed."""

    # Lines ((x, z), (x, z)) where a leg is missing; empty to hide them.
    gaps_changed = Signal(object)

    def __init__(
        self,
        context: EditContext,
        ask_choices: ChoiceRequest,
        costmap_provider: Callable[[], NavigationCostmap | None] = lambda: None,
        vehicle_provider: Callable[[], Vehicle] = Vehicle,
        curve_radius_provider: Callable[[], float] = lambda: CURVE_RADIUS,
        height_for_new_node: Callable[[AutoDriveData, float, float], float] = lambda *_: 0.0,
        run_generator: GeneratorRunner = run_directly,
        show_missing: Callable[[list[str]], None] = lambda lines: None,
        parent=None,
    ):
        super().__init__(context, parent)

        self.ask_choices = ask_choices
        self.costmap_provider = costmap_provider
        self.vehicle_provider = vehicle_provider
        self.curve_radius_provider = curve_radius_provider
        self.height_for_new_node = height_for_new_node
        self.run_generator = run_generator
        self.show_missing = show_missing

    def create_for(self, stops: list[Stop]) -> bool:
        autodrive_data = self.autodrive_data_provider()

        if autodrive_data is None or self.edit_history.history_locked or not stops:
            return False

        self.gaps_changed.emit([])
        answer = self.ask_choices(stops, autodrive_data)

        return answer is not None and self.create(*answer)

    def create(self, choices: list[StopChoice], settings: StationSettings) -> bool:
        if not choices:
            return False

        autodrive_data = self.autodrive_data_provider()
        costmap, vehicle = self.costmap_provider(), self.vehicle_provider()
        radius = self.curve_radius_provider()
        finder = RouteFinder(costmap, vehicle) if costmap is not None else None

        def work(report, cancelled):
            def find_route(request):
                return None if cancelled() else finder.find(request, cancelled)

            joins = []

            for index, choice in enumerate(choices):
                if cancelled():
                    return None

                report(index, len(choices), choice.name)
                joins.append(
                    plan_direct(
                        autodrive_data,
                        choice,
                        settings,
                        radius,
                        costmap,
                        vehicle,
                        find_route if finder is not None else None,
                    )
                )

            return joins

        joins = self.run_generator(tr("Create station lanes"), work)

        if joins is None:
            return False

        command, open_ends = direct_command(
            autodrive_data, choices, joins, settings, self.height_for_new_node
        )
        self.edit_history.push(command)

        if self.node_selection is not None and open_ends:
            self.node_selection.replace(set(open_ends), open_ends[0])

        self.gaps_changed.emit([gap for join in joins for gap in join.gaps])
        missing = [
            f"{choice.name}: {', '.join(join.missing)}"
            for choice, join in zip(choices, joins, strict=True)
            if not (join.has_way_in and join.has_way_out)
        ]

        if missing:
            self.status_changed.emit(
                tr(
                    "{count} station lanes created; {missing} have no way in or out, their "
                    "lane ends are selected",
                    count=len(choices),
                    missing=len(missing),
                )
            )
            self.show_missing(missing)
        else:
            self.status_changed.emit(
                tr("{count} station lanes created and joined to the roads", count=len(choices))
            )

        return True
