from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QObject

from autodrive_editor.editing.operations.network_check import NetworkCheckOperation
from autodrive_editor.model.autodrive_data import AutoDriveData
from autodrive_editor.network_check.checks import ALL_CHECKS, CheckResults, check_network
from autodrive_editor.network_check.ignores import (
    CheckIgnores,
    IgnoreStore,
    ignore_keys,
    split_ignored,
)
from autodrive_editor.settings.app_settings import AppSettings
from autodrive_editor.terrain.terrain_follower import TerrainHeightProvider
from autodrive_editor.ui.panels.check_dock import CheckDock


class NetworkCheckController(QObject):
    """Runs the network check and shows the results in the check dock;
    fixes, ignores and switches off checks from there. Ignored entries and
    switched-off checks are kept per network file."""

    def __init__(
        self,
        dock: CheckDock,
        operation: NetworkCheckOperation,
        settings: AppSettings,
        ignore_store: IgnoreStore,
        autodrive_data: Callable[[], AutoDriveData | None],
        network_path: Callable[[], Path | None],
        map_scale: Callable[[], int],
        terrain_height_at: Callable[[], TerrainHeightProvider | None],
        parent=None,
    ):
        super().__init__(parent)

        self.dock = dock
        self.operation = operation
        self.ignore_store = ignore_store
        self.autodrive_data = autodrive_data
        self.network_path = network_path
        self.map_scale = map_scale
        self.terrain_height_at = terrain_height_at

        self.ignores = CheckIgnores()

        dock.check_requested.connect(self.run)
        dock.tolerances_changed.connect(settings.set_check_tolerances)
        dock.checks_changed.connect(self.set_enabled_checks)
        dock.fix_requested.connect(self.fix)
        dock.ignore_requested.connect(self.ignore)
        dock.unignore_requested.connect(self.unignore)

    def network_loaded(self):
        """Loads the ignores of the new network and clears the old results."""

        path = self.network_path()
        self.ignores = self.ignore_store.load(path) if path is not None else CheckIgnores()

        self.dock.set_enabled_checks(self.ignores.enabled_checks)
        self.dock.set_results(None)

    def run(self):
        autodrive_data = self.autodrive_data()

        if autodrive_data is None:
            return

        overlap_tolerance, max_height_difference = self.dock.tolerances

        results = check_network(
            autodrive_data,
            self.map_scale(),
            self.terrain_height_at(),
            overlap_tolerance,
            max_height_difference,
            checks=self.ignores.enabled_checks,
        )

        self.dock.set_results(*split_ignored(autodrive_data, results, self.ignores.ignored))
        self.dock.show()
        self.dock.raise_()

    def fix(self, results: CheckResults):
        """Fixes the problems, one undo step per kind, then checks again."""

        if results.overlapping_groups:
            self.operation.merge_overlapping(results.overlapping_groups)

        if results.outside_node_ids:
            self.operation.move_onto_map(results.outside_node_ids)

        if results.height_problems:
            self.operation.set_heights_from_terrain(
                [problem.node_id for problem in results.height_problems]
            )

        self.run()

    def ignore(self, results: CheckResults):
        self._change_ignores(lambda keys: self.ignores.ignored.update(keys), results)

    def unignore(self, results: CheckResults):
        self._change_ignores(lambda keys: self.ignores.ignored.difference_update(keys), results)

    def set_enabled_checks(self, checks):
        self.ignores.disabled_checks = set(ALL_CHECKS) - set(checks)
        self._save()
        self.run()

    def _change_ignores(self, change: Callable[[set], None], results: CheckResults):
        autodrive_data = self.autodrive_data()

        if autodrive_data is None:
            return

        change(ignore_keys(autodrive_data, results))
        self._save()
        self.run()

    def _save(self):
        path = self.network_path()

        if path is not None:
            self.ignore_store.save(path, self.ignores)
