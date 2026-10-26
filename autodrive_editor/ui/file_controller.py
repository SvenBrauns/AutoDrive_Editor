from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtWidgets import QFileDialog, QInputDialog, QMessageBox, QWidget

from autodrive_editor.editing.edit_history import EditHistory
from autodrive_editor.file_io.routes_index import find_route_entry, read_routes_index
from autodrive_editor.game.savegame_info import savegames_with_autodrive
from autodrive_editor.i18n import tr
from autodrive_editor.project.autosave import AutosaveStore
from autodrive_editor.project.project_coordinator import ProjectCoordinator
from autodrive_editor.settings.app_settings import AppSettings
from autodrive_editor.ui.dialogs.list_choice_dialog import ListChoiceDialog
from autodrive_editor.ui.dialogs.messages import APP_TITLE, inform


class FileController(QObject):
    """The File menu: opens routes, savegames, XML files, map images and
    projects, saves them, keeps an autosave of unsaved changes and asks
    before unsaved changes would be lost."""

    status_changed = Signal(str)

    # Data was saved; the window title shows the new name.
    saved = Signal()

    def __init__(
        self,
        window: QWidget,
        settings: AppSettings,
        project_coordinator: ProjectCoordinator,
        edit_history: EditHistory,
        autosave_store: AutosaveStore,
        projects_directory: Path,
    ):
        super().__init__(window)

        self.window = window
        self.settings = settings
        self.project_coordinator = project_coordinator
        self.edit_history = edit_history
        self.projects_directory = projects_directory

        # Unsaved changes are backed up here regularly.
        self.autosave_store = autosave_store
        self.autosave_timer = QTimer(self)
        self.autosave_timer.timeout.connect(self.autosave)
        self.apply_autosave_interval()

    def select_background(self):
        filename, _ = QFileDialog.getOpenFileName(
            self.window, tr("Choose overview.dds"), "", tr("DDS images (*.dds);;All files (*)")
        )

        if not filename:
            return

        try:
            self.project_coordinator.load_background_file(filename)

        except Exception as ex:
            self.status_changed.emit(tr("The DDS could not be loaded: {error}", error=ex))

    def select_heightmap(self):
        filename, _ = QFileDialog.getOpenFileName(
            self.window, tr("Choose dem.png"), "", tr("PNG heightmaps (*.png);;All files (*)")
        )

        if not filename:
            return

        try:
            self.project_coordinator.load_heightmap_file(filename)

        except Exception as ex:
            self.status_changed.emit(tr("The heightmap could not be loaded: {error}", error=ex))

    def open_route(self):
        if not self.confirm_discard_changes():
            return

        game_folder = self._valid_game_folder()

        if game_folder is None:
            return

        if not game_folder.routes_xml_path.is_file():
            self._inform(
                tr(
                    "No AutoDrive route list was found in the game folder:\n{path}\n\n"
                    "Routes are created in the game with AutoDrive's RoutesManager.",
                    path=game_folder.routes_xml_path,
                )
            )
            return

        try:
            entries = [
                entry
                for entry in read_routes_index(game_folder.routes_xml_path)
                if entry.path.is_file()
            ]
        except ValueError as ex:
            self._inform(str(ex))
            return

        if not entries:
            self._inform(tr("The route list contains no existing routes."))
            return

        entry = self._choose(
            tr("Open route"),
            tr(
                "Routes from AutoDrive's RoutesManager. "
                "AutoDrive can reload them in a running game."
            ),
            [tr("Name"), tr("Map"), tr("Revision"), tr("Date")],
            [
                ([entry.name, entry.map_name, str(entry.revision), entry.date], entry)
                for entry in entries
            ],
            sort_column=3,
            newest_first=True,
        )

        if entry is None:
            return

        self._load_config(entry.path, display_name=entry.name, map_name=entry.map_name)

    def open_savegame(self):
        if not self.confirm_discard_changes():
            return

        game_folder = self._valid_game_folder()

        if game_folder is None:
            return

        savegames = savegames_with_autodrive(game_folder)

        if not savegames:
            self._inform(tr("No savegame in the game folder contains AutoDrive data."))
            return

        savegame = self._choose(
            tr("Open savegame"),
            tr("Savegames with AutoDrive data (AutoDrive_config.xml)."),
            [tr("No."), tr("Name"), tr("Map"), tr("Saved")],
            [
                (
                    [f"{info.number:2d}", info.display_name, info.map_title, info.save_date],
                    info,
                )
                for info in savegames
            ],
        )

        if savegame is None:
            return

        self._load_config(savegame.autodrive_config_path, display_name=savegame.display_name)

    def load_xml(self):
        if not self.confirm_discard_changes():
            return

        game_folder = self.settings.game_folder
        start = ""

        if game_folder is not None and game_folder.routes_directory.is_dir():
            start = str(game_folder.routes_directory)

        filename, _ = QFileDialog.getOpenFileName(
            self.window, tr("Open AutoDrive XML"), start, tr("AutoDrive XML (*.xml)")
        )

        if not filename:
            return

        try:
            self.project_coordinator.load_xml_file(filename)

        except Exception as ex:
            self.status_changed.emit(tr("The XML could not be loaded: {error}", error=ex))

    def _load_config(self, path, display_name=None, map_name=None):
        try:
            self.project_coordinator.load_xml_file(
                path, display_name=display_name, map_name=map_name
            )
        except Exception as ex:
            self._inform(tr("The AutoDrive data could not be loaded:\n{error}", error=ex))

    def _valid_game_folder(self):
        """The configured FS25 folder, or None after telling the user how
        to set one."""

        game_folder = self.settings.game_folder

        if game_folder is None or not game_folder.is_valid:
            self._inform(
                tr("No valid FS25 game folder is set.\nPlease set it under File → Settings.")
            )
            return None

        return game_folder

    def _choose(self, title, hint, columns, rows, sort_column=0, newest_first=False):
        dialog = ListChoiceDialog(
            title,
            hint,
            columns,
            rows,
            sort_column=sort_column,
            newest_first=newest_first,
            parent=self.window,
        )

        return dialog.chosen_value if dialog.exec() else None

    def save_xml(self) -> bool:
        if self.project_coordinator.config_source is None:
            self.status_changed.emit(tr("Load an AutoDrive XML first"))
            return False

        try:
            affected_vehicles = self.project_coordinator.save_xml_file()
        except Exception as ex:
            self._inform(tr("The AutoDrive data could not be saved:\n{error}", error=ex))
            return False

        self._after_save(affected_vehicles)

        return True

    def save_xml_as(self) -> bool:
        """Routes from the RoutesManager are saved as a new route there,
        everything else into a file chosen in a dialog."""

        source = self.project_coordinator.config_source

        if source is None:
            self.status_changed.emit(tr("Load an AutoDrive XML first"))
            return False

        affected_vehicles = []

        try:
            if find_route_entry(source.path) is not None:
                name = self._ask_route_name(source.display_name)

                if not name:
                    return False

                self.project_coordinator.save_as_route(name, source.map_name or "")
            else:
                target = self._ask_save_path(source.path)

                if target is None:
                    return False

                affected_vehicles = self.project_coordinator.save_as_file(target)
        except Exception as ex:
            self._inform(tr("The AutoDrive data could not be saved:\n{error}", error=ex))
            return False

        self._after_save(affected_vehicles)

        return True

    def _after_save(self, affected_vehicles: list[str]):
        self.edit_history.mark_clean()
        self.autosave_store.clear()
        self.saved.emit()

        if affected_vehicles:
            self._inform(
                tr(
                    "These vehicles had a deleted marker as their target. The target is now "
                    "marker 1, a parking target was removed:"
                )
                + "\n\n"
                + "\n".join(affected_vehicles)
            )

    def _ask_route_name(self, default_name: str | None) -> str | None:
        name, accepted = QInputDialog.getText(
            self.window, tr("Save as new route"), tr("Name of the route:"), text=default_name or ""
        )

        return name.strip() if accepted else None

    def _ask_save_path(self, current_path: Path) -> Path | None:
        filename, _ = QFileDialog.getSaveFileName(
            self.window, tr("Save as"), str(current_path), tr("AutoDrive XML (*.xml)")
        )

        if not filename:
            return None

        return Path(filename if filename.lower().endswith(".xml") else filename + ".xml")

    def autosave(self):
        """Backs up unsaved changes into the editor's data folder."""

        if self.project_coordinator.config_source is None or self.edit_history.is_clean:
            return

        try:
            self.project_coordinator.write_autosave(self.autosave_store)
        except Exception as ex:
            self.status_changed.emit(tr("Autosave failed: {error}", error=ex))
            return

        self.status_changed.emit(tr("Autosaved at {time:%H:%M}", time=datetime.now()))

    def offer_autosave_restore(self):
        """After the editor ended with unsaved changes, offers to restore
        them from the autosave."""

        info = self.autosave_store.read()

        if info is None:
            return

        if not Path(info.source_path).is_file():
            self._inform(
                tr(
                    "There is an autosave of “{name}”, but the original file is missing:\n"
                    "{source}\n\nThe autosave can be loaded with “Open XML file…”:\n{autosave}",
                    name=info.display_name,
                    source=info.source_path,
                    autosave=self.autosave_store.xml_path,
                )
            )
            return

        if not self._ask_restore_autosave(info):
            self.autosave_store.clear()
            return

        try:
            self.project_coordinator.restore_autosave(self.autosave_store, info)
        except Exception as ex:
            self._inform(tr("The autosave could not be loaded:\n{error}", error=ex))
            return

        self.edit_history.mark_unsaved()

    def _ask_restore_autosave(self, info) -> bool:
        answer = QMessageBox.question(
            self.window,
            APP_TITLE,
            tr(
                "The editor was closed with unsaved changes to “{name}”. "
                "Restore the autosave from {time}?",
                name=info.display_name,
                time=info.saved_at,
            ),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )

        return answer == QMessageBox.Yes

    def apply_autosave_interval(self):
        minutes = self.settings.autosave_minutes

        if minutes > 0:
            self.autosave_timer.start(minutes * 60_000)
        else:
            self.autosave_timer.stop()

    def confirm_discard_changes(self) -> bool:
        """Offers to save unsaved changes before they would be lost. Returns
        whether to go on. Going on drops the autosave as well."""

        if self.edit_history.is_clean:
            self.autosave_store.clear()
            return True

        answer = self._ask_save_changes()

        if answer == QMessageBox.Save:
            return self.save_xml()

        if answer == QMessageBox.Discard:
            self.autosave_store.clear()
            return True

        return False

    def _ask_save_changes(self):
        return QMessageBox.question(
            self.window,
            APP_TITLE,
            tr("The changes are not saved yet. Save now?"),
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
            QMessageBox.Save,
        )

    def _inform(self, message: str):
        inform(self.window, message)

    def save_project(self):
        if self.project_coordinator.config_source is None:
            self.status_changed.emit(tr("Load an AutoDrive XML first"))
            return

        default_path = self.project_coordinator.current_config_path or str(self.projects_directory)

        config_path, _ = QFileDialog.getSaveFileName(
            self.window, tr("Save project"), default_path, tr("JSON project (*.json)")
        )

        if not config_path:
            return

        if not config_path.lower().endswith(".json"):
            config_path += ".json"

        try:
            self.project_coordinator.save_project_file(config_path)

        except Exception as ex:
            self.status_changed.emit(tr("The project could not be saved: {error}", error=ex))

    def load_project(self):
        if not self.confirm_discard_changes():
            return

        config_path, _ = QFileDialog.getOpenFileName(
            self.window,
            tr("Open project"),
            str(self.projects_directory),
            tr("JSON project (*.json)"),
        )

        if not config_path:
            return

        try:
            self.project_coordinator.load_project_file(config_path)

        except Exception as ex:
            self.status_changed.emit(tr("The project could not be loaded: {error}", error=ex))
