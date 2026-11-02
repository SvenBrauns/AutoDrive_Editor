import html
from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager, nullcontext
from dataclasses import replace
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QInputDialog,
    QMessageBox,
    QWidget,
)

from autodrive_editor.editing.commands.replace_network import ReplaceNetworkCommand
from autodrive_editor.editing.edit_history import EditHistory
from autodrive_editor.file_io.autodrive_xml import AutoDriveXmlReader, ConfigFormat
from autodrive_editor.file_io.routes_index import (
    RouteEntry,
    find_route_entry,
    read_routes_index,
    routes_index_for,
)
from autodrive_editor.game.savegame_info import SavegameInfo, read_savegame_info, savegames
from autodrive_editor.i18n import tr
from autodrive_editor.project.autosave import AutosaveStore
from autodrive_editor.project.project_coordinator import ProjectCoordinator
from autodrive_editor.project.route_match import same_network
from autodrive_editor.settings.app_settings import AppSettings
from autodrive_editor.settings.recent_items import (
    RecentItem,
    RecentKind,
    with_recent_item,
    without_recent_item,
)
from autodrive_editor.ui.dialogs.list_choice_dialog import ListChoiceDialog
from autodrive_editor.ui.dialogs.messages import APP_TITLE, inform
from autodrive_editor.ui.dialogs.open_dialog import OpenDialog
from autodrive_editor.ui.panels.open_screen import OpenLists, OpenScreen, settings_link


class FileController(QObject):
    """The File menu: opens routes, savegames, XML files and map images,
    saves them, keeps an autosave of unsaved changes and asks
    before unsaved changes would be lost."""

    status_changed = Signal(str)

    # Data was saved; the window title shows the new name.
    saved = Signal()

    # The user opened AutoDrive data or an autosave.
    config_opened = Signal()

    def __init__(
        self,
        window: QWidget,
        settings: AppSettings,
        project_coordinator: ProjectCoordinator,
        edit_history: EditHistory,
        autosave_store: AutosaveStore,
    ):
        super().__init__(window)

        self.window = window
        self.settings = settings
        self.project_coordinator = project_coordinator
        self.edit_history = edit_history

        # Suggested by Save as route…: the route last saved or opened in this session.
        self.last_route_name: str | None = None

        # Asked before saving; False cancels the save.
        self.confirm_save: Callable[[], bool] = lambda: True

        # Opens the settings dialog (the Open screen links to it).
        self.open_settings: Callable[[], None] = lambda: None

        # Asked first before the data would be replaced or the editor closed; False cancels.
        self.confirm_end_plan: Callable[[], bool] = lambda: True
        self.confirm_end_capture: Callable[[], bool] = lambda: True

        # Shows a text on the map and a wait cursor while the block runs.
        self.busy: Callable[[str], AbstractContextManager] = lambda text: nullcontext()

        # Unsaved changes are backed up here regularly.
        self.autosave_store = autosave_store
        self.autosave_timer = QTimer(self)
        self.autosave_timer.timeout.connect(self.autosave)
        self.apply_autosave_interval()
        edit_history.planning_changed.connect(self._handle_planning_changed)

    def open(self):
        """File → Open…: the Open screen as a dialog."""

        if not self.confirm_discard_changes() or not self.confirm_end_capture():
            return

        self._open_choice(self._ask_open())

    def open_chosen(self, choice):
        """Opens a savegame or route picked on the Open screen on the map."""

        if self.confirm_discard_changes() and self.confirm_end_capture():
            self._open_choice(choice)

    def open_other_file(self):
        if self.confirm_discard_changes() and self.confirm_end_capture():
            self._browse_xml()

    def _open_choice(self, choice):
        if isinstance(choice, RouteEntry):
            self._open_route(choice)
        elif isinstance(choice, SavegameInfo):
            self._open_savegame(choice)
        elif choice == OpenDialog.BROWSE:
            self._browse_xml()

    def open_lists(self) -> OpenLists:
        """The savegames and routes the Open screen offers, with hints for empty lists."""

        game_folder = self.settings.game_folder

        if game_folder is None or not game_folder.is_valid:
            hint = settings_link(tr("No valid FS25 game folder is set."))
            return OpenLists(savegames_hint=hint, routes_hint=hint)

        found = savegames(game_folder)
        routes, routes_hint = self._routes(game_folder)

        return OpenLists(
            savegames=found,
            savegames_hint="" if found else settings_link(tr("No savegames found.")),
            routes=routes,
            routes_hint=routes_hint,
        )

    @staticmethod
    def _routes(game_folder) -> tuple[list[RouteEntry], str]:
        """The routes of the RoutesManager whose files exist, and the hint for an empty list."""

        no_routes = tr(
            "No routes found. Routes are created in the game with AutoDrive's RoutesManager."
        )

        if not game_folder.routes_xml_path.is_file():
            return [], no_routes

        try:
            entries = read_routes_index(game_folder.routes_xml_path)
        except ValueError as ex:
            return [], html.escape(str(ex))

        entries = [entry for entry in entries if entry.path.is_file()]

        return entries, "" if entries else no_routes

    def _ask_open(self):
        """The chosen route or savegame, OpenDialog.BROWSE or None."""

        dialog = OpenDialog(self.open_lists(), self.window)
        dialog.open_screen.settings_requested.connect(
            lambda: self._settings_from(dialog.open_screen)
        )
        result = dialog.exec()

        if result == OpenDialog.BROWSE:
            return OpenDialog.BROWSE

        return dialog.chosen_value if result == QDialog.DialogCode.Accepted else None

    def _settings_from(self, screen: OpenScreen):
        """The settings link of the Open screen; the lists follow a new game folder."""

        self.open_settings()
        screen.set_lists(self.open_lists())

    def _open_route(self, entry: RouteEntry):
        if self._load_config(entry.path, display_name=entry.name, map_name=entry.map_name):
            self.last_route_name = entry.name
            self._remember(
                RecentItem(RecentKind.ROUTE, str(entry.path), entry.name, entry.map_name)
            )

    def _open_savegame(self, savegame: SavegameInfo):
        path = savegame.autodrive_config_path

        if not savegame.has_autodrive:
            # Not listed under Open recent until Save has created the file.
            self.project_coordinator.start_empty_savegame(
                path, savegame.display_name, savegame.autodrive_map_name
            )
            self.config_opened.emit()
            return

        if self._load_config(path, display_name=savegame.display_name):
            self._remember(RecentItem(RecentKind.SAVEGAME, str(path), savegame.display_name))

    def _browse_xml(self):
        game_folder = self.settings.game_folder
        start = ""

        if game_folder is not None and game_folder.routes_directory.is_dir():
            start = str(game_folder.routes_directory)

        filename, _ = QFileDialog.getOpenFileName(
            self.window, tr("Open AutoDrive XML"), start, tr("AutoDrive XML (*.xml)")
        )

        if filename:
            self._load_xml(filename)

    def _load_xml(self, filename):
        try:
            with self._loading(Path(filename).name):
                self.project_coordinator.load_xml_file(filename)

        except Exception as ex:
            self.status_changed.emit(tr("The XML could not be loaded: {error}", error=ex))
            return

        path = Path(filename)
        self._remember(RecentItem(RecentKind.XML, str(path), path.name))
        self.config_opened.emit()

    def _load_config(self, path, display_name=None, map_name=None) -> bool:
        try:
            with self._loading(display_name or Path(path).name):
                self.project_coordinator.load_xml_file(
                    path, display_name=display_name, map_name=map_name
                )
        except Exception as ex:
            self._inform(tr("The AutoDrive data could not be loaded:\n{error}", error=ex))
            return False

        self.config_opened.emit()
        return True

    @contextmanager
    def _loading(self, name: str) -> Iterator[None]:
        text = tr("Loading “{name}”…", name=name)
        self.status_changed.emit(text)

        try:
            with self.busy(text):
                yield
        except Exception:
            self.status_changed.emit(tr("“{name}” could not be loaded", name=name))
            raise

    def open_recent(self, item: RecentItem):
        """Opens a file from the recent list. A file that is gone is removed
        from the list."""

        if not self.confirm_discard_changes() or not self.confirm_end_capture():
            return

        if not Path(item.path).is_file():
            self._set_recent_items(without_recent_item(self.settings.recent_items, item))
            self._inform(tr("The file no longer exists:\n{path}", path=item.path))
            return

        self._open_item(item)

    def open_at_startup(self):
        """Offers to restore an autosave; if none is restored, opens the last
        opened file again (if that is turned on and the file still exists)."""

        self.offer_autosave_restore()

        if self.project_coordinator.config_source is not None or not self.settings.reopen_last:
            return

        items = self.settings.recent_items

        if items and Path(items[0].path).is_file():
            self._open_item(items[0])

    def _open_item(self, item: RecentItem):
        if item.kind == RecentKind.SAVEGAME:
            # The name may have changed in the game, and older entries lack the folder.
            item = replace(item, name=read_savegame_info(Path(item.path).parent).display_name)

        if item.kind == RecentKind.XML:
            self._load_xml(item.path)

        elif self._load_config(item.path, display_name=item.name, map_name=item.map_name):
            self._remember(item)

    def clear_recent_items(self):
        self._set_recent_items([])

    def _remember(self, item: RecentItem):
        self._set_recent_items(with_recent_item(self.settings.recent_items, item))

    def _set_recent_items(self, items: list[RecentItem]):
        self.settings.set_recent_items(items)

    def save_xml(self) -> bool:
        if self.project_coordinator.config_source is None:
            self.status_changed.emit(tr("Load an AutoDrive XML first"))
            return False

        if self._file_changed_on_disk():
            answer = self._ask_overwrite_changed_file()

            if answer == QMessageBox.Discard and self.confirm_end_capture():
                self._reload()

            if answer != QMessageBox.Save:
                return False

        if not self.confirm_save():
            return False

        vehicles = self.project_coordinator.vehicles_losing_markers()

        if vehicles and not self._ask_save_vehicle_targets(vehicles):
            return False

        try:
            self.project_coordinator.save_xml_file()
        except Exception as ex:
            self._inform(tr("The AutoDrive data could not be saved:\n{error}", error=ex))
            return False

        self._after_save()

        return True

    def _file_changed_on_disk(self) -> bool:
        QApplication.setOverrideCursor(Qt.WaitCursor)

        try:
            return self.project_coordinator.file_changed_on_disk()
        finally:
            QApplication.restoreOverrideCursor()

    def _ask_overwrite_changed_file(self):
        """QMessageBox.Save overwrites, Discard reloads, Cancel cancels."""

        box = QMessageBox(
            QMessageBox.Warning,
            APP_TITLE,
            tr(
                "“{name}” was changed by someone else since it was opened or saved, "
                "probably by the game. Saving overwrites these changes.",
                name=self.project_coordinator.config_source.display_name,
            ),
            parent=self.window,
        )
        box.addButton(tr("Save anyway"), QMessageBox.AcceptRole)
        box.addButton(tr("Reload (my changes are lost)"), QMessageBox.DestructiveRole)
        box.addButton(QMessageBox.Cancel)
        box.setDefaultButton(QMessageBox.Cancel)
        box.exec()

        return {
            QMessageBox.AcceptRole: QMessageBox.Save,
            QMessageBox.DestructiveRole: QMessageBox.Discard,
        }.get(box.buttonRole(box.clickedButton()), QMessageBox.Cancel)

    def reload(self):
        """File → Reload: loads the open file again from disk; unsaved changes are lost."""

        source = self.project_coordinator.config_source

        if source is None or not self.confirm_end_plan() or not self.confirm_end_capture():
            return

        if self.edit_history.is_clean or self._confirm_reload(source.display_name):
            self._reload()

    def _confirm_reload(self, name: str) -> bool:
        answer = QMessageBox.question(
            self.window,
            APP_TITLE,
            tr("Reload “{name}” from disk? The unsaved changes are lost.", name=name),
            QMessageBox.Yes | QMessageBox.Cancel,
            QMessageBox.Cancel,
        )

        return answer == QMessageBox.Yes

    def _reload(self):
        try:
            with self._loading(self.project_coordinator.config_source.display_name):
                self.project_coordinator.reload_file()
        except Exception as ex:
            self._inform(tr("The AutoDrive data could not be loaded:\n{error}", error=ex))
            return

        self.autosave_store.clear()

    def save_as_route(self) -> bool:
        """File → Save as route…: keeps a version of the network in the RoutesManager. A route
        of the RoutesManager is saved next to it, anything else into the game folder's."""

        source = self.project_coordinator.config_source

        if source is None:
            self.status_changed.emit(tr("Load an AutoDrive XML first"))
            return False

        routes_xml_path = self._routes_xml_for(source)

        if routes_xml_path is None:
            self._inform(tr("No valid FS25 game folder is set."))
            return False

        if not self.confirm_save():
            return False

        name = self._ask_route_name(self._suggested_route_name(source))

        if not name:
            return False

        if self._route_exists(routes_xml_path, name) and not self._confirm_replace_route(name):
            return False

        try:
            self.project_coordinator.save_as_route(name, routes_xml_path)
        except Exception as ex:
            self._inform(tr("The AutoDrive data could not be saved:\n{error}", error=ex))
            return False

        self.last_route_name = name

        # A savegame stays open with its own unsaved state.
        if source.format != ConfigFormat.SAVEGAME:
            self._after_save()

        return True

    def load_route_into_savegame(self) -> bool:
        """File → Load route into savegame…: replaces the savegame's network with a route of
        its map, as one undo step. Offers to keep the current network as a route first if no
        route holds it."""

        source = self.project_coordinator.config_source
        data = self.project_coordinator.autodrive_data
        game_folder = self.settings.game_folder

        if source is None or source.format != ConfigFormat.SAVEGAME or not self.confirm_end_plan():
            return False

        routes = []

        if game_folder is not None and game_folder.routes_xml_path.is_file():
            routes = [
                entry
                for entry in read_routes_index(game_folder.routes_xml_path)
                if entry.map_name == source.map_name and entry.path.is_file()
            ]

        if not routes:
            self._inform(tr("The RoutesManager has no routes of this map."))
            return False

        if not any(same_network(data, AutoDriveXmlReader.load(e.path)) for e in routes):
            answer = self._ask_save_network_first()

            if answer == QMessageBox.Cancel or (
                answer == QMessageBox.Yes and not self.save_as_route()
            ):
                return False

        entry = self._choose_route(routes)

        if entry is None:
            return False

        self.edit_history.push(
            ReplaceNetworkCommand(
                data,
                AutoDriveXmlReader.load(entry.path),
                tr("Load route “{name}”", name=entry.name),
            )
        )
        self.project_coordinator.show_parking()
        self.last_route_name = entry.name
        self.status_changed.emit(
            tr("Route “{name}” loaded; Save writes it into the savegame", name=entry.name)
        )

        return True

    def _ask_save_network_first(self):
        return QMessageBox.question(
            self.window,
            APP_TITLE,
            tr("No route holds the current network. Save the current network as a route first?"),
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
            QMessageBox.Yes,
        )

    def _choose_route(self, routes: list[RouteEntry]) -> RouteEntry | None:
        dialog = ListChoiceDialog(
            tr("Load route into savegame"),
            tr("Routes of this map in the RoutesManager:"),
            [tr("Name"), tr("Revision"), tr("Date")],
            [([entry.name, str(entry.revision), entry.date], entry) for entry in routes],
            ok_text=tr("Load"),
            sort_column=2,
            newest_first=True,
            parent=self.window,
        )

        return dialog.chosen_value if dialog.exec() == QDialog.DialogCode.Accepted else None

    def _routes_xml_for(self, source) -> Path | None:
        if find_route_entry(source.path) is not None:
            return routes_index_for(source.path)

        game_folder = self.settings.game_folder

        return (
            game_folder.routes_xml_path
            if game_folder is not None and game_folder.is_valid
            else None
        )

    def _suggested_route_name(self, source) -> str:
        """The route last saved or opened, else the map name."""

        return self.last_route_name or source.map_name or ""

    @staticmethod
    def _route_exists(routes_xml_path: Path, name: str) -> bool:
        if not routes_xml_path.is_file():
            return False

        return any(entry.name == name for entry in read_routes_index(routes_xml_path))

    def _confirm_replace_route(self, name: str) -> bool:
        answer = QMessageBox.question(
            self.window,
            APP_TITLE,
            tr("Replace route “{name}”? It gets a new revision.", name=name),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        return answer == QMessageBox.Yes

    def _after_save(self):
        self.edit_history.mark_clean()
        self.autosave_store.clear()
        self.saved.emit()

    def _ask_save_vehicle_targets(self, vehicles: list[str]) -> bool:
        text = (
            tr(
                "These vehicles have a deleted marker as their target. Saving sets the target "
                "to marker 1 and removes a parking target:"
            )
            + "\n\n"
            + "\n".join(vehicles)
            + "\n\n"
            + tr("Save anyway?")
        )
        answer = QMessageBox.question(
            self.window, APP_TITLE, text, QMessageBox.Save | QMessageBox.Cancel, QMessageBox.Cancel
        )

        return answer == QMessageBox.Save

    def _ask_route_name(self, default_name: str) -> str | None:
        name, accepted = QInputDialog.getText(
            self.window, tr("Save as route"), tr("Name of the route:"), text=default_name
        )

        return name.strip() if accepted else None

    def autosave(self):
        """Backs up unsaved changes into the editor's data folder. The edits of an open plan
        are left out: the timer waits while planning, the edits before the plan were backed
        up when it started."""

        if not self.edit_history.is_planning:
            self._write_autosave()

    def _handle_planning_changed(self, planning: bool):
        if planning and self.autosave_timer.isActive():
            self._write_autosave()

    def _write_autosave(self):
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
                    "{source}\n\n"
                    "The autosave can be loaded with “Open…” → “Open other file…”:\n{autosave}",
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
            with self._loading(info.display_name):
                self.project_coordinator.restore_autosave(self.autosave_store, info)
        except Exception as ex:
            self._inform(tr("The autosave could not be loaded:\n{error}", error=ex))
            return

        self.edit_history.mark_unsaved()
        self.config_opened.emit()

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
        whether to go on. Going on drops the autosave as well. An open plan is applied or
        discarded first."""

        if not self.confirm_end_plan():
            return False

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
