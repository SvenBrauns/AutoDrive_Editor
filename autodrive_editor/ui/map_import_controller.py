import shutil

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox, QProgressDialog, QWidget

from autodrive_editor.file_io.autodrive_xml import ConfigFormat, ConfigSource
from autodrive_editor.file_io.base_game_maps import read_base_game_maps
from autodrive_editor.file_io.map_mod import MapMod, read_map_mod
from autodrive_editor.game.map_source import (
    READ_ERRORS,
    MapSource,
    find_by_map_id,
    find_by_map_name,
    find_import_source,
)
from autodrive_editor.game.savegame_info import read_savegame_info
from autodrive_editor.i18n import tr
from autodrive_editor.project.project_coordinator import ProjectCoordinator
from autodrive_editor.settings.app_settings import AppSettings
from autodrive_editor.terrain.game_picture import PICTURE_FOLDER
from autodrive_editor.terrain.map_cache import CachedMap, MapCache, folder_size
from autodrive_editor.ui.dialogs.first_start_dialog import FirstStartDialog
from autodrive_editor.ui.dialogs.messages import APP_TITLE, inform


class MapImportController(QObject):
    """Imports map images and heightmaps from map mods and the base game when a file to be
    opened names a map that is not imported yet, and runs Settings → Maps."""

    status_changed = Signal(str)

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

        # Missing maps that were not found or not imported in this session; not asked again.
        self.declined_missing_maps = set()

    def import_map_mod(self):
        map_mod = self._choose_map_mod()

        if map_mod is not None:
            self._import_maps([(map_mod, entry) for entry in map_mod.maps])

    def run_first_start(self):
        """Shows the setup dialog on the first start (or when a stored folder is gone). Maps are
        imported when a file needs them."""

        if not self.settings.needs_setup:
            return

        self._show_first_start_dialog()
        self.settings.mark_setup_done()

    def _show_first_start_dialog(self):
        FirstStartDialog(self.settings, parent=self.window).exec()

    def reimport(self, cached: CachedMap) -> bool:
        """Settings → Maps → Re-import: reads the map from its mod again."""

        game_folder = self.settings.game_folder
        mods = game_folder.mods_directory if game_folder is not None else None
        found = find_import_source(cached, mods, self._read_base_game_maps())

        if found is None:
            self._inform(tr("The mod “{mod}” of this map was not found.", mod=cached.mod_name))
            return False

        return bool(self._import_maps([found]))

    def remove(self, cached: CachedMap) -> bool:
        """Settings → Maps → Remove: deletes the imported map with its game picture, after
        asking."""

        picture_bytes = folder_size(cached.directory / PICTURE_FOLDER)

        if not self._confirm_remove(cached.title, picture_bytes):
            return False

        if self.project_coordinator.loaded_map() == cached:
            self.project_coordinator.unload_map()

        try:
            shutil.rmtree(cached.directory)
        except OSError as ex:
            self._inform(tr("The map could not be removed:\n{error}", error=ex))
            return False

        self.status_changed.emit(tr("Map “{name}” removed", name=cached.title))
        return True

    def _confirm_remove(self, title: str, picture_bytes: int) -> bool:
        text = tr("Remove the imported map “{name}”?", name=title)

        if picture_bytes:
            text += "\n\n" + tr(
                "Its game picture ({size} MB) is deleted too.", size=f"{picture_bytes / 1e6:.0f}"
            )

        answer = QMessageBox.question(
            self.window, APP_TITLE, text, QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )

        return answer == QMessageBox.Yes

    def use_for_open_file(self, cached: CachedMap):
        """Settings → Maps → Use this map for the open file; remembered for that file."""

        source = self.project_coordinator.config_source

        if source is None or not cached.autodrive_names:
            return

        self.settings.set_file_map(source.path, cached.autodrive_names[0])
        self.project_coordinator.use_map(cached.autodrive_names[0])

    def ensure_map(self, source: ConfigSource):
        """Before a file is shown: imports its map if it is missing, without asking. A savegame
        names the mod in careerSavegame.xml; for a route the mods are scanned. Asks only if the
        map is not found."""

        name = source.map_name

        if not name or self.map_cache.find(name) is not None or name in self.declined_missing_maps:
            return

        found = self._find_map(source)

        if found is None:
            # The question comes while the file loads, under its wait cursor.
            QApplication.setOverrideCursor(Qt.ArrowCursor)

            try:
                found = self._ask_map_not_found(name)
            finally:
                QApplication.restoreOverrideCursor()

        if found is None:
            self.declined_missing_maps.add(name)
            return

        self._import_maps([found], show_now=False)

    def _find_map(self, source: ConfigSource) -> MapSource | None:
        game_folder = self.settings.game_folder
        mods = game_folder.mods_directory if game_folder is not None else None
        base_maps = self._read_base_game_maps()

        try:
            if source.format == ConfigFormat.SAVEGAME:
                map_id = read_savegame_info(source.path.parent).map_id
                return find_by_map_id(map_id, mods, base_maps) if map_id else None

            return find_by_map_name(source.map_name, mods, base_maps)
        except READ_ERRORS:
            return None

    def _ask_map_not_found(self, map_name: str) -> MapSource | None:
        """Asks for the mod zip of a map that was not found; None to go on without the map."""

        box = QMessageBox(self.window)
        box.setWindowTitle(APP_TITLE)
        box.setIcon(QMessageBox.Icon.Question)
        box.setText(tr("The map “{name}” was not found in the mods folder.", name=map_name))
        box.setInformativeText(tr("Without map image and heightmap only the nodes are shown."))
        choose_button = box.addButton(tr("Choose mod zip…"), QMessageBox.ButtonRole.AcceptRole)
        box.addButton(tr("Continue without map"), QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(choose_button)
        box.exec()

        if box.clickedButton() is not choose_button:
            return None

        map_mod = self._choose_map_mod()

        if map_mod is None:
            return None

        found = next(
            ((map_mod, entry) for entry in map_mod.maps if map_name in entry.autodrive_names),
            (map_mod, map_mod.maps[0]) if len(map_mod.maps) == 1 else None,
        )

        if found is None:
            self._inform(tr("This mod does not contain the map “{name}”.", name=map_name))

        return found

    def _choose_map_mod(self) -> MapMod | None:
        """A map mod chosen in a file dialog; None if cancelled or not a map mod."""

        game_folder = self.settings.game_folder
        start = str(game_folder.mods_directory) if game_folder is not None else ""

        filename, _ = QFileDialog.getOpenFileName(
            self.window, tr("Import map mod"), start, tr("Mod archive (*.zip)")
        )

        if not filename:
            return None

        try:
            map_mod = read_map_mod(filename)
        except Exception as ex:
            self._inform(tr("The mod could not be read:\n{error}", error=ex))
            return None

        if map_mod is None:
            self._inform(tr("This mod contains no map."))

        return map_mod

    def _read_base_game_maps(self):
        """The base game maps, if the FS25 install folder is known."""

        installation = self.settings.install_folder

        if installation is None or not installation.is_valid:
            return None

        try:
            return read_base_game_maps(installation.data_directory)
        except Exception:
            return None

    def _import_maps(self, chosen, show_now=True):
        """Imports the given (mod, map) pairs into the map cache and reports the result.
        show_now shows a new map under the open file right away; False when a file is about to
        be opened with it."""

        progress = QProgressDialog(tr("Importing maps…"), tr("Cancel"), 0, len(chosen), self.window)
        progress.setWindowTitle(tr("Import maps"))
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        # A single map imports in one blocking step; shown at once so the user sees why.
        progress.setMinimumDuration(300 if len(chosen) > 1 else 0)

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

        # Shows a new or re-imported map (e.g. now with its ground map) right away.
        if imported and show_now:
            self.project_coordinator.load_map_for_current_config()

        message = tr("{count} map(s) imported.", count=len(imported))

        if failed:
            message += "\n\n" + tr("Not imported:") + "\n" + "\n".join(failed)

        self.status_changed.emit(tr("{count} map(s) imported", count=len(imported)))

        if failed:
            self._inform(message)

        return imported

    def _inform(self, message: str):
        inform(self.window, message)
