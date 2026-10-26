from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox, QProgressDialog, QWidget

from autodrive_editor.file_io.base_game_maps import read_base_game_maps
from autodrive_editor.file_io.map_mod import read_map_mod
from autodrive_editor.game.map_scanner import ScanResult, scan_for_map_mods
from autodrive_editor.i18n import tr
from autodrive_editor.project.project_coordinator import ProjectCoordinator
from autodrive_editor.settings.app_settings import AppSettings
from autodrive_editor.terrain.map_cache import MapCache
from autodrive_editor.ui.dialogs.first_start_dialog import FirstStartDialog
from autodrive_editor.ui.dialogs.map_import_dialog import MapImportDialog
from autodrive_editor.ui.dialogs.messages import APP_TITLE, inform


class MapImportController(QObject):
    """Imports map images and heightmaps from map mods and the base game:
    on first start, from the menu, and when a loaded config names a map
    that is not imported yet."""

    status_changed = Signal(str)

    MISSING_MAP_SCAN = "scan"
    MISSING_MAP_IMPORT = "import"

    def __init__(
        self,
        window: QWidget,
        settings: AppSettings,
        map_cache: MapCache,
        project_coordinator: ProjectCoordinator,
    ):
        super().__init__(window)

        self.window = window
        self.settings = settings
        self.map_cache = map_cache
        self.project_coordinator = project_coordinator

        # Missing maps the user chose to go on without in this session.
        self.declined_missing_maps = set()

    def import_map_mod(self):
        game_folder = self.settings.game_folder
        start = str(game_folder.mods_directory) if game_folder is not None else ""

        filename, _ = QFileDialog.getOpenFileName(
            self.window, tr("Import map mod"), start, tr("Mod archive (*.zip)")
        )

        if not filename:
            return

        try:
            map_mod = read_map_mod(filename)
        except Exception as ex:
            self._inform(tr("The mod could not be read:\n{error}", error=ex))
            return

        if map_mod is None:
            self._inform(tr("This mod contains no map."))
            return

        self._import_maps([(map_mod, entry) for entry in map_mod.maps])

    def run_first_start(self):
        """Shows the setup dialog on the first start (or when a stored folder
        is gone) and scans for maps if the user wants to."""

        if not self.settings.needs_setup:
            return

        scan_requested = self._show_first_start_dialog()
        self.settings.mark_setup_done()

        if scan_requested:
            self.scan_map_mods()

    def _show_first_start_dialog(self) -> bool:
        dialog = FirstStartDialog(self.settings, parent=self.window)
        dialog.exec()

        return dialog.scan_requested

    def scan_map_mods(self):
        """Offers the base game maps and the map mods for import. Works with
        only one of the two folders set."""

        game_folder = self.settings.game_folder
        has_game_folder = game_folder is not None and game_folder.is_valid
        base_maps = self._read_base_game_maps()

        if not has_game_folder and base_maps is None:
            self._inform(
                tr(
                    "Neither a valid FS25 game folder nor an FS25 installation is set.\n"
                    "Please set them under File → Settings."
                )
            )
            return

        result = scan_for_map_mods(game_folder.mods_directory) if has_game_folder else ScanResult()

        if base_maps is not None:
            result.map_mods.insert(0, base_maps)

        if not result.map_mods:
            self._inform(
                tr(
                    "No map mods were found in the mods folder:\n{path}",
                    path=game_folder.mods_directory,
                )
            )
            return

        chosen = self._choose_maps_to_import(result)

        if chosen:
            self._import_maps(chosen)

    def offer_missing_map(self, map_name: str):
        """Called when a loaded config names a map that is not imported.
        Offers to import it and loads it right away."""

        if map_name in self.declined_missing_maps:
            return

        choice = self._ask_missing_map(map_name)

        if choice == self.MISSING_MAP_SCAN:
            self.scan_map_mods()
        elif choice == self.MISSING_MAP_IMPORT:
            self.import_map_mod()
        else:
            self.declined_missing_maps.add(map_name)
            return

        if not self.project_coordinator.load_map_for_current_config():
            self.status_changed.emit(tr("Map “{name}” is still not imported", name=map_name))

    def _ask_missing_map(self, map_name: str) -> str | None:
        box = QMessageBox(self.window)
        box.setWindowTitle(APP_TITLE)
        box.setIcon(QMessageBox.Icon.Question)
        box.setText(tr("The map “{name}” is not imported yet.", name=map_name))
        box.setInformativeText(
            tr("Without map image and heightmap only the nodes are shown. Import the map now?")
        )

        scan_button = box.addButton(tr("Scan maps…"), QMessageBox.ButtonRole.AcceptRole)
        import_button = box.addButton(tr("Import from mod…"), QMessageBox.ButtonRole.ActionRole)
        box.addButton(tr("Continue without map"), QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(scan_button)
        box.exec()

        clicked = box.clickedButton()

        if clicked is scan_button:
            return self.MISSING_MAP_SCAN

        if clicked is import_button:
            return self.MISSING_MAP_IMPORT

        return None

    def _read_base_game_maps(self):
        """The base game maps, if the FS25 install folder is known."""

        installation = self.settings.install_folder

        if installation is None or not installation.is_valid:
            return None

        try:
            return read_base_game_maps(installation.data_directory)
        except Exception:
            return None

    def _choose_maps_to_import(self, scan_result):
        dialog = MapImportDialog(
            scan_result.map_mods, self.map_cache, scan_result.skipped, parent=self.window
        )

        return dialog.chosen_maps if dialog.exec() else []

    def _import_maps(self, chosen):
        """Imports the given (mod, map) pairs into the map cache and reports
        the result."""

        progress = QProgressDialog(tr("Importing maps…"), tr("Cancel"), 0, len(chosen), self.window)
        progress.setWindowTitle(tr("Import maps"))
        progress.setMinimumDuration(300)

        imported, failed = [], []

        for index, (map_mod, entry) in enumerate(chosen):
            if progress.wasCanceled():
                break

            progress.setLabelText(f"{entry.title} ({index + 1}/{len(chosen)})")
            progress.setValue(index)
            QApplication.processEvents()

            try:
                self.map_cache.import_map(map_mod, entry)
                imported.append(entry.title)
            except Exception as ex:
                failed.append(f"{entry.title}: {ex}")

        progress.setValue(len(chosen))

        message = tr("{count} map(s) imported.", count=len(imported))

        if failed:
            message += "\n\n" + tr("Not imported:") + "\n" + "\n".join(failed)

        self.status_changed.emit(tr("{count} map(s) imported", count=len(imported)))

        if failed:
            self._inform(message)

        return imported

    def _inform(self, message: str):
        inform(self.window, message)
