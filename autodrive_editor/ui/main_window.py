from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QGraphicsScene,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressDialog,
    QVBoxLayout,
)

from autodrive_editor.editing.commands.edit_command import DataChange
from autodrive_editor.editing.edit_history import EditHistory
from autodrive_editor.editing.operations.align_nodes import AlignNodesOperation
from autodrive_editor.editing.operations.clipboard import ClipboardOperation
from autodrive_editor.editing.operations.connect_nodes import ConnectNodesOperation
from autodrive_editor.editing.operations.create_nodes import CreateNodesOperation
from autodrive_editor.editing.operations.delete_nodes import DeleteNodesOperation
from autodrive_editor.editing.operations.markers import MarkerOperation
from autodrive_editor.editing.operations.move_nodes import MoveNodesOperation
from autodrive_editor.editing.operations.node_position import NodePositionOperation
from autodrive_editor.editing.operations.node_types import NodeTypeOperation
from autodrive_editor.editing.operations.reverse_direction import ReverseDirectionOperation
from autodrive_editor.editing.operations.rotate_selection import RotateSelectionOperation
from autodrive_editor.file_io.base_game_maps import read_base_game_maps
from autodrive_editor.file_io.map_mod import read_map_mod
from autodrive_editor.file_io.project_file import ProjectFileStore
from autodrive_editor.file_io.routes_index import find_route_entry, read_routes_index
from autodrive_editor.game.map_scanner import ScanResult, scan_for_map_mods
from autodrive_editor.game.savegame_info import savegames_with_autodrive
from autodrive_editor.measurement.controller import MeasurementController
from autodrive_editor.measurement.coordinator import MeasurementCoordinator
from autodrive_editor.measurement.mode import MeasurementMode
from autodrive_editor.model.autodrive_data import (
    REGULAR_FLAG,
    SUBPRIO_FLAG,
    AutoDriveData,
    NodeData,
)
from autodrive_editor.model.connections import ConnectionType
from autodrive_editor.paths import LOCAL_PROJECTS_DIRECTORY, MARKER_ICON_PATH, user_data_directory
from autodrive_editor.project.autosave import AutosaveStore
from autodrive_editor.project.project_coordinator import ProjectCoordinator
from autodrive_editor.rendering.display_style import DisplayStyle
from autodrive_editor.rendering.scene_renderer import SceneRenderer
from autodrive_editor.selection.node_selection import NodeSelection
from autodrive_editor.selection.selection_coordinator import SelectionCoordinator
from autodrive_editor.settings.app_settings import AppSettings
from autodrive_editor.terrain.background_map import BackgroundMap
from autodrive_editor.terrain.heightmap import Heightmap
from autodrive_editor.terrain.map_cache import MapCache
from autodrive_editor.ui.actions.main_window_actions import MainWindowActions
from autodrive_editor.ui.controls.grid_coordinator import GridCoordinator
from autodrive_editor.ui.dialogs.first_start_dialog import FirstStartDialog
from autodrive_editor.ui.dialogs.list_choice_dialog import ListChoiceDialog
from autodrive_editor.ui.dialogs.map_import_dialog import MapImportDialog
from autodrive_editor.ui.dialogs.marker_dialog import MarkerDialog
from autodrive_editor.ui.dialogs.node_position_dialog import NodePositionDialog
from autodrive_editor.ui.dialogs.settings_dialog import SettingsDialog
from autodrive_editor.ui.map_view.map_view import MapView
from autodrive_editor.ui.map_view.rotation_controller import ViewRotationController
from autodrive_editor.ui.panels.debug_dock import DebugDock
from autodrive_editor.ui.panels.debug_dock_coordinator import DebugDockCoordinator
from autodrive_editor.ui.panels.display_options_dialog import DisplayOptionsDialog
from autodrive_editor.ui.panels.marker_dock import MarkerDock
from autodrive_editor.ui.panels.node_info_formatter import NodeInfoFormatter
from autodrive_editor.ui.panels.welcome_panel import WelcomePanel
from autodrive_editor.ui.tools.connect_nodes_tool import ConnectNodesTool
from autodrive_editor.ui.tools.create_node_tool import CreateNodeTool
from autodrive_editor.ui.tools.delete_nodes_tool import DeleteNodesTool
from autodrive_editor.ui.tools.interaction_mode import InteractionMode
from autodrive_editor.ui.tools.measure_tool import MeasureTool
from autodrive_editor.ui.tools.move_nodes_tool import MoveNodesTool
from autodrive_editor.ui.tools.node_click_tool import NodeClickTool
from autodrive_editor.ui.tools.rotate_selection_tool import RotateSelectionTool
from autodrive_editor.ui.tools.select_tool import SelectTool
from autodrive_editor.ui.tools.toggle_node_type_tool import ToggleNodeTypeTool


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

    WINDOW_TITLE = "AutoDrive FS25 Editor"
    INITIAL_WIDTH = 1400
    INITIAL_HEIGHT = 900

    NO_FILE_STATUS = "Keine Datei geladen"
    NO_SELECTION_INFO = "Keine Node ausgewählt"

    DEFAULT_MAP_SCALE = 1

    # How far from a connection line a click still hits it, in pixels.
    CONNECTION_CLICK_TOLERANCE = 6.0

    MISSING_MAP_SCAN = "scan"
    MISSING_MAP_IMPORT = "import"

    def __init__(self):
        super().__init__()

        self.local_projects_directory = LOCAL_PROJECTS_DIRECTORY

        # Detects the FS25 folder on first start and keeps it afterwards.
        self.settings = AppSettings()
        self.settings.ensure_game_folder()
        self.settings.ensure_install_folder()

        # Map images and heightmaps imported from map mods.
        self.map_cache = MapCache()

        # Missing maps the user chose to go on without in this session.
        self.declined_missing_maps = set()

        self._configure_window()
        self._create_scene_and_view()

        self._create_map_layers()
        self._create_selection_and_measurement()
        self._create_edit_operations()
        self._register_map_tools()
        self._create_project_coordinator()

        self._create_status_widgets()
        self._create_central_widget()
        self._create_marker_dock()
        self._create_debug_dock()

        self.scene_renderer.set_marker_names_visible(self.settings.marker_names_visible)

        self.actions = MainWindowActions(self)
        self.actions.set_current_map_scale(self.background_map.map_scale)

        self._create_welcome_panel()
        self._create_grid_coordinator()
        self._connect_signals()

        # Created after the renderer is connected to the view, so the
        # dock reads the renderer state after it has been updated.
        self._create_debug_dock_coordinator()

        # Unsaved changes are backed up here regularly.
        self.autosave_store = AutosaveStore(user_data_directory() / "autosave")
        self.autosave_timer = QTimer(self)
        self.autosave_timer.timeout.connect(self.autosave)
        self._apply_autosave_interval()

    def select_background(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "overview.dds auswählen", "", "DDS-Bilder (*.dds);;Alle Dateien (*)"
        )

        if not filename:
            return

        try:
            self.project_coordinator.load_background_file(filename)

        except Exception as ex:
            self._set_status(f"DDS konnte nicht geladen werden: {ex}")

    def select_heightmap(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "dem.png auswählen", "", "PNG-Heightmaps (*.png);;Alle Dateien (*)"
        )

        if not filename:
            return

        try:
            self.project_coordinator.load_heightmap_file(filename)

        except Exception as ex:
            self._set_status(f"Heightmap konnte nicht geladen werden: {ex}")

    def remove_heightmap(self):
        self.project_coordinator.remove_heightmap()

    def set_map_scale(self, map_scale: int):
        action = self.actions.map_scale_actions.get(map_scale)

        map_scale_label = action.text() if action is not None else str(map_scale)

        try:
            self.project_coordinator.set_map_scale(
                map_scale=map_scale, map_scale_label=map_scale_label
            )

        except Exception as ex:
            self._set_status(f"Kartengröße konnte nicht geändert werden: {ex}")

    def import_map_mod(self):
        game_folder = self.settings.game_folder
        start = str(game_folder.mods_directory) if game_folder is not None else ""

        filename, _ = QFileDialog.getOpenFileName(
            self, "Kartenmod importieren", start, "Mod-Archiv (*.zip)"
        )

        if not filename:
            return

        try:
            map_mod = read_map_mod(filename)
        except Exception as ex:
            self._inform(f"Der Mod konnte nicht gelesen werden:\n{ex}")
            return

        if map_mod is None:
            self._inform("Dieser Mod enthält keine Karte.")
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
        dialog = FirstStartDialog(self.settings, parent=self)
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
                "Es ist weder ein gültiger FS25-Spielordner noch eine LS25-Installation "
                "eingestellt.\nBitte unter Datei → Einstellungen festlegen."
            )
            return

        result = scan_for_map_mods(game_folder.mods_directory) if has_game_folder else ScanResult()

        if base_maps is not None:
            result.map_mods.insert(0, base_maps)

        if not result.map_mods:
            self._inform(
                f"Im Mods-Ordner wurden keine Kartenmods gefunden:\n{game_folder.mods_directory}"
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
            self._set_status(f"Karte „{map_name}“ ist weiterhin nicht importiert")

    def _ask_missing_map(self, map_name: str) -> str | None:
        box = QMessageBox(self)
        box.setWindowTitle(self.WINDOW_TITLE)
        box.setIcon(QMessageBox.Icon.Question)
        box.setText(f"Die Karte „{map_name}“ ist noch nicht importiert.")
        box.setInformativeText(
            "Ohne Kartenbild und Heightmap werden nur die Nodes angezeigt. Karte jetzt importieren?"
        )

        scan_button = box.addButton("Karten scannen…", QMessageBox.ButtonRole.AcceptRole)
        import_button = box.addButton("Aus Mod importieren…", QMessageBox.ButtonRole.ActionRole)
        box.addButton("Ohne Karte weiter", QMessageBox.ButtonRole.RejectRole)
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
            scan_result.map_mods, self.map_cache, scan_result.skipped, parent=self
        )

        return dialog.chosen_maps if dialog.exec() else []

    def _import_maps(self, chosen):
        """Imports the given (mod, map) pairs into the map cache and reports
        the result."""

        progress = QProgressDialog("Karten werden importiert…", "Abbrechen", 0, len(chosen), self)
        progress.setWindowTitle("Karten importieren")
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

        message = f"{len(imported)} Karte(n) importiert."

        if failed:
            message += "\n\nNicht importiert:\n" + "\n".join(failed)

        self._set_status(f"{len(imported)} Karte(n) importiert")

        if failed:
            self._inform(message)

        return imported

    def open_route(self):
        if not self._confirm_discard_changes():
            return

        game_folder = self._valid_game_folder()

        if game_folder is None:
            return

        if not game_folder.routes_xml_path.is_file():
            self._inform(
                "Im Spielordner wurde keine AutoDrive-Routenliste gefunden:\n"
                f"{game_folder.routes_xml_path}\n\n"
                "Routen entstehen im Spiel über den RoutesManager von AutoDrive."
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
            self._inform("Die Routenliste enthält keine vorhandenen Routen.")
            return

        entry = self._choose(
            "Route öffnen",
            "Routen aus dem RoutesManager von AutoDrive. AutoDrive kann sie im laufenden "
            "Spiel neu laden.",
            ["Name", "Karte", "Revision", "Datum"],
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
        if not self._confirm_discard_changes():
            return

        game_folder = self._valid_game_folder()

        if game_folder is None:
            return

        savegames = savegames_with_autodrive(game_folder)

        if not savegames:
            self._inform("Kein Savegame im Spielordner enthält AutoDrive-Daten.")
            return

        savegame = self._choose(
            "Savegame öffnen",
            "Savegames mit AutoDrive-Daten (AutoDrive_config.xml).",
            ["Nr.", "Name", "Karte", "Gespeichert"],
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
        if not self._confirm_discard_changes():
            return

        game_folder = self.settings.game_folder
        start = ""

        if game_folder is not None and game_folder.routes_directory.is_dir():
            start = str(game_folder.routes_directory)

        filename, _ = QFileDialog.getOpenFileName(
            self, "AutoDrive-XML öffnen", start, "AutoDrive-XML (*.xml)"
        )

        if not filename:
            return

        try:
            self.project_coordinator.load_xml_file(filename)

        except Exception as ex:
            self._set_status(f"XML konnte nicht geladen werden: {ex}")

    def load_xml_file(self, filename):
        self.project_coordinator.load_xml_file(filename)

    def _load_config(self, path, display_name=None, map_name=None):
        try:
            self.project_coordinator.load_xml_file(
                path, display_name=display_name, map_name=map_name
            )
        except Exception as ex:
            self._inform(f"Die AutoDrive-Daten konnten nicht geladen werden:\n{ex}")

    def _valid_game_folder(self):
        """The configured FS25 folder, or None after telling the user how
        to set one."""

        game_folder = self.settings.game_folder

        if game_folder is None or not game_folder.is_valid:
            self._inform(
                "Es ist kein gültiger FS25-Spielordner eingestellt.\n"
                "Bitte unter Datei → Einstellungen festlegen."
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
            parent=self,
        )

        return dialog.chosen_value if dialog.exec() else None

    def save_xml(self) -> bool:
        if self.project_coordinator.config_source is None:
            self._set_status("Bitte zuerst eine AutoDrive-XML laden")
            return False

        try:
            affected_vehicles = self.project_coordinator.save_xml_file()
        except Exception as ex:
            self._inform(f"Die AutoDrive-Daten konnten nicht gespeichert werden:\n{ex}")
            return False

        self._after_save(affected_vehicles)

        return True

    def save_xml_as(self) -> bool:
        """Routes from the RoutesManager are saved as a new route there,
        everything else into a file chosen in a dialog."""

        source = self.project_coordinator.config_source

        if source is None:
            self._set_status("Bitte zuerst eine AutoDrive-XML laden")
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
            self._inform(f"Die AutoDrive-Daten konnten nicht gespeichert werden:\n{ex}")
            return False

        self._after_save(affected_vehicles)

        return True

    def _after_save(self, affected_vehicles: list[str]):
        self.edit_history.mark_clean()
        self.autosave_store.clear()
        self._update_window_title()

        if affected_vehicles:
            self._inform(
                "Diese Fahrzeuge hatten einen gelöschten Marker als Ziel. Das Ziel ist jetzt "
                "Marker 1, ein Parkziel wurde entfernt:\n\n" + "\n".join(affected_vehicles)
            )

    def _ask_route_name(self, default_name: str | None) -> str | None:
        name, accepted = QInputDialog.getText(
            self, "Als neue Route speichern", "Name der Route:", text=default_name or ""
        )

        return name.strip() if accepted else None

    def _ask_save_path(self, current_path: Path) -> Path | None:
        filename, _ = QFileDialog.getSaveFileName(
            self, "Speichern unter", str(current_path), "AutoDrive-XML (*.xml)"
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
            self._set_status(f"Automatische Sicherung fehlgeschlagen: {ex}")
            return

        self._set_status(f"Automatisch gesichert um {datetime.now():%H:%M}")

    def offer_autosave_restore(self):
        """After the editor ended with unsaved changes, offers to restore
        them from the autosave."""

        info = self.autosave_store.read()

        if info is None:
            return

        if not Path(info.source_path).is_file():
            self._inform(
                f"Es gibt eine automatische Sicherung von „{info.display_name}“, aber die "
                f"Originaldatei fehlt:\n{info.source_path}\n\n"
                f"Die Sicherung kann über „XML-Datei öffnen…“ geladen werden:\n"
                f"{self.autosave_store.xml_path}"
            )
            return

        if not self._ask_restore_autosave(info):
            self.autosave_store.clear()
            return

        try:
            self.project_coordinator.restore_autosave(self.autosave_store, info)
        except Exception as ex:
            self._inform(f"Die automatische Sicherung konnte nicht geladen werden:\n{ex}")
            return

        self.edit_history.mark_unsaved()

    def _ask_restore_autosave(self, info) -> bool:
        answer = QMessageBox.question(
            self,
            self.WINDOW_TITLE,
            f"Der Editor wurde mit ungespeicherten Änderungen an „{info.display_name}“ beendet. "
            f"Die automatische Sicherung vom {info.saved_at} wiederherstellen?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )

        return answer == QMessageBox.Yes

    def _apply_autosave_interval(self):
        minutes = self.settings.autosave_minutes

        if minutes > 0:
            self.autosave_timer.start(minutes * 60_000)
        else:
            self.autosave_timer.stop()

    def _confirm_discard_changes(self) -> bool:
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
            self,
            self.WINDOW_TITLE,
            "Die Änderungen sind noch nicht gespeichert. Jetzt speichern?",
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
            QMessageBox.Save,
        )

    def closeEvent(self, event):
        if self._confirm_discard_changes():
            event.accept()
        else:
            event.ignore()

    def _inform(self, message: str):
        QMessageBox.information(self, self.WINDOW_TITLE, message)

    def save_project(self):
        if not self.project_coordinator.current_xml_path:
            self._set_status("Bitte zuerst eine AutoDrive-XML laden")
            return

        default_path = (
            self.project_coordinator.current_config_path
            if self.project_coordinator.current_config_path
            else str(self.local_projects_directory)
        )

        config_path, _ = QFileDialog.getSaveFileName(
            self, "Projektkonfiguration speichern", default_path, "JSON-Konfiguration (*.json)"
        )

        if not config_path:
            return

        if not config_path.lower().endswith(".json"):
            config_path += ".json"

        try:
            self.project_coordinator.save_project_file(config_path)

        except Exception as ex:
            self._set_status(f"Projekt konnte nicht gespeichert werden: {ex}")

    def load_project(self):
        if not self._confirm_discard_changes():
            return

        config_path, _ = QFileDialog.getOpenFileName(
            self,
            "Projektkonfiguration öffnen",
            str(self.local_projects_directory),
            "JSON-Konfiguration (*.json)",
        )

        if not config_path:
            return

        try:
            self.project_coordinator.load_project_file(config_path)

        except Exception as ex:
            self._set_status(f"Projekt konnte nicht geladen werden: {ex}")

    def show_node_info(self, node_data: NodeData):
        self.selection_coordinator.show_node_info(node_data)

    def set_interaction_mode(self, interaction_mode: InteractionMode):
        self.view.set_interaction_mode(interaction_mode)

        status_text = f"Modus: {interaction_mode.display_name}"

        status_hint = self.view.active_tool.status_hint()

        if status_hint:
            status_text += f" – {status_hint}"

        self._set_status(status_text)

    def set_view_rotation(self, rotation_angle: float):
        self.view.set_rotation_angle(rotation_angle)

        self._set_status(f"Rotation: {self.view.rotation_angle:.2f}°")

    def set_view_rotation_step(self, rotation_step: float):
        self.view.set_rotation_step(rotation_step)

        self._set_status(f"Rotationsraster: {self.view.rotation_step:.2f}°")

    def reset_view_rotation(self):
        self.view.reset_view_rotation()

        self._set_status("Rotation zurückgesetzt")

    def set_measurement_mode(self, measurement_mode: MeasurementMode):
        self.measurement_coordinator.set_mode(measurement_mode)

    def delete_selection(self):
        self.delete_nodes_operation.delete_selection()

    def align_view_to_measurement(self):
        self.measurement_coordinator.align_view_to_measurement()

    def open_settings(self):
        dialog = SettingsDialog(self.settings, parent=self)

        if dialog.exec():
            self._apply_autosave_interval()

            folder = self.settings.game_folder

            if folder is None:
                self._set_status("Kein Spielordner gesetzt")
            elif folder.is_valid:
                self._set_status(f"Spielordner: {folder.path}")
            else:
                self._set_status(f"Spielordner ist kein FS25-Benutzerordner: {folder.path}")

    def set_marker_names_visible(self, visible: bool):
        self.scene_renderer.set_marker_names_visible(visible)
        self.settings.set_marker_names_visible(visible)

    def focus_marker(self, node_id: int):
        """Centers the map on a marker's node and selects it."""

        autodrive_data = self._get_autodrive_data()
        node = autodrive_data.get_node(node_id) if autodrive_data is not None else None

        if node is None:
            return

        # Zoom in far enough for the marker to be drawn.
        marker_zoom = self.scene_renderer.display_style.marker_min_zoom

        if self.view.zoom_level < marker_zoom:
            self.view.set_zoom_level(marker_zoom)

        self.view.centerOn(node.x, node.z)
        self.node_selection.replace({node_id}, node_id)

    def rename_marker_group(self, name: str):
        new_name = self._ask_group_name(name)

        if new_name is not None:
            self.marker_operation.rename_group(name, new_name)

    def _ask_group_name(self, name: str) -> str | None:
        new_name, accepted = QInputDialog.getText(
            self, "Markergruppe umbenennen", "Neuer Name:", text=name
        )

        return new_name if accepted else None

    def _ask_node_position(self, node):
        dialog = NodePositionDialog(node.node_id, node.x, node.y, node.z, parent=self)

        return dialog.values if dialog.exec() else None

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
            raise TypeError("Der Darstellungsstil ist ungültig.")

        self.scene_renderer.set_display_style(display_style)

        self.project_coordinator.rebuild_scene_after_style_change()

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

        self.measurement_controller = MeasurementController(scene=self.scene, parent=self)

        self.measurement_coordinator = MeasurementCoordinator(
            view=self.view,
            controller=self.measurement_controller,
            node_item_provider=self.selection_coordinator.get_node_item_at,
            parent=self,
        )

    def _create_edit_operations(self):
        """The undo history and every operation that changes the data."""

        self.edit_history = EditHistory(parent=self)

        self.move_nodes_operation = MoveNodesOperation(
            view=self.view,
            selection_coordinator=self.selection_coordinator,
            node_selection=self.node_selection,
            edit_history=self.edit_history,
            autodrive_data_provider=self._get_autodrive_data,
            terrain_height_at=self._get_terrain_height,
            snap_point=self.background_map.snap_point,
            parent=self,
        )

        self.delete_nodes_operation = DeleteNodesOperation(
            selection_coordinator=self.selection_coordinator,
            node_selection=self.node_selection,
            edit_history=self.edit_history,
            autodrive_data_provider=self._get_autodrive_data,
            parent=self,
        )

        self.connect_nodes_operation = ConnectNodesOperation(
            selection_coordinator=self.selection_coordinator,
            edit_history=self.edit_history,
            autodrive_data_provider=self._get_autodrive_data,
            parent=self,
        )

        self.rotate_selection_operation = RotateSelectionOperation(
            node_selection=self.node_selection,
            edit_history=self.edit_history,
            autodrive_data_provider=self._get_autodrive_data,
            terrain_height_at=self._get_terrain_height,
            parent=self,
        )

        self.create_nodes_operation = CreateNodesOperation(
            view=self.view,
            selection_coordinator=self.selection_coordinator,
            edit_history=self.edit_history,
            autodrive_data_provider=self._get_autodrive_data,
            terrain_height_at=self._get_terrain_height,
            snap_point=self.background_map.snap_point,
            parent=self,
        )

        self.node_type_operation = NodeTypeOperation(
            selection_coordinator=self.selection_coordinator,
            node_selection=self.node_selection,
            edit_history=self.edit_history,
            autodrive_data_provider=self._get_autodrive_data,
            parent=self,
        )

        self.clipboard_operation = ClipboardOperation(
            node_selection=self.node_selection,
            edit_history=self.edit_history,
            autodrive_data_provider=self._get_autodrive_data,
            delete_nodes=self.delete_nodes_operation.delete_nodes,
            # Looked up on each call, so tests can replace it.
            paste_position=lambda: self._get_paste_position(),
            terrain_height_at=self._get_terrain_height,
            parent=self,
        )

        self.align_nodes_operation = AlignNodesOperation(
            view=self.view,
            selection_coordinator=self.selection_coordinator,
            node_selection=self.node_selection,
            edit_history=self.edit_history,
            autodrive_data_provider=self._get_autodrive_data,
            terrain_height_at=self._get_terrain_height,
            parent=self,
        )

        self.node_position_operation = NodePositionOperation(
            selection_coordinator=self.selection_coordinator,
            edit_history=self.edit_history,
            autodrive_data_provider=self._get_autodrive_data,
            # Looked up on each call, so tests can replace _ask_node_position.
            ask_position=lambda node: self._ask_node_position(node),
            parent=self,
        )

        self.reverse_direction_operation = ReverseDirectionOperation(
            connection_at=self._get_connection_at,
            node_selection=self.node_selection,
            edit_history=self.edit_history,
            autodrive_data_provider=self._get_autodrive_data,
            parent=self,
        )

        self.marker_operation = MarkerOperation(
            selection_coordinator=self.selection_coordinator,
            node_selection=self.node_selection,
            edit_history=self.edit_history,
            autodrive_data_provider=self._get_autodrive_data,
            # Looked up on each call, so tests can replace _ask_marker.
            ask_marker=lambda *args: self._ask_marker(*args),
            parent=self,
        )

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
            parent=self,
        )

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
                "Connection anklicken, um ihre Richtung umzukehren",
                is_target=lambda view_position: self._get_connection_at(view_position) is not None,
            ),
        )

        self.view.register_tool(
            InteractionMode.MOVE_NODES, MoveNodesTool(self.view, self.move_nodes_operation)
        )

        self.view.register_tool(
            InteractionMode.EDIT_NODE_POSITION,
            NodeClickTool(
                self.view,
                self.node_position_operation.edit_at,
                "Node anklicken, um ihre Position einzugeben",
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

        self._register_marker_tools()

        self.view.register_measure_tool(MeasureTool(self.view, self.measurement_coordinator))

    def _register_align_tools(self):
        operation = self.align_nodes_operation
        reference_hint = "Nodes auswählen, dann die Referenz-Node anklicken"

        tools = (
            (InteractionMode.ALIGN_HORIZONTAL, operation.align_horizontal_at, reference_hint),
            (InteractionMode.ALIGN_VERTICAL, operation.align_vertical_at, reference_hint),
            (InteractionMode.ALIGN_HEIGHT, operation.align_height_at, reference_hint),
            (
                InteractionMode.HEIGHT_FROM_TERRAIN,
                operation.height_from_terrain_at,
                "Nodes auswählen, dann eine Node anklicken",
            ),
        )

        for interaction_mode, click, hint in tools:
            self.view.register_tool(interaction_mode, NodeClickTool(self.view, click, hint))

    def _register_marker_tools(self):
        operation = self.marker_operation

        def move_hint():
            if operation.move_source_id is None:
                return "Node mit Marker anklicken, um den Marker aufzunehmen"

            return "Ziel-Node anklicken (Rechtsklick oder Esc bricht ab)"

        tools = (
            (InteractionMode.ADD_MARKER, operation.add_at, "Node ohne Marker anklicken", None),
            (InteractionMode.EDIT_MARKER, operation.edit_at, "Node mit Marker anklicken", None),
            (InteractionMode.MOVE_MARKER, operation.move_click, move_hint, operation.cancel_move),
            (InteractionMode.DELETE_MARKER, operation.delete_at, "Node mit Marker anklicken", None),
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

    def _create_marker_dock(self):
        self.marker_dock = MarkerDock(self)

        self.addDockWidget(Qt.RightDockWidgetArea, self.marker_dock)

        self.marker_dock.marker_activated.connect(self.focus_marker)
        self.marker_dock.edit_requested.connect(self.marker_operation.edit_marker)
        self.marker_dock.rename_group_requested.connect(self.rename_marker_group)
        self.marker_dock.delete_group_requested.connect(self.marker_operation.delete_group)

    def _create_debug_dock(self):
        self.debug_dock = DebugDock(self)

        self.addDockWidget(Qt.RightDockWidgetArea, self.debug_dock)

        self.debug_dock.set_node_info(self.NO_SELECTION_INFO)

        self.debug_dock.hide()

    def _connect_signals(self):
        self.view.zoom_changed.connect(self.scene_renderer.update_visibility_for_zoom)

        self.view.visible_scene_rect_changed.connect(self.scene_renderer.update_visible_scene_rect)

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

        self.project_coordinator.map_missing.connect(self.offer_missing_map)

        self.edit_history.clean_changed.connect(self._handle_edit_clean_changed)

        self.edit_history.data_changed.connect(self._handle_data_changed)

        self.move_nodes_operation.status_changed.connect(self._set_status)

        self.delete_nodes_operation.status_changed.connect(self._set_status)

        self.connect_nodes_operation.status_changed.connect(self._set_status)

        self.create_nodes_operation.status_changed.connect(self._set_status)

        self.node_type_operation.status_changed.connect(self._set_status)

        self.marker_operation.status_changed.connect(self._set_status)

        self.reverse_direction_operation.status_changed.connect(self._set_status)

        self.clipboard_operation.status_changed.connect(self._set_status)

        self.node_position_operation.status_changed.connect(self._set_status)

        self.align_nodes_operation.status_changed.connect(self._set_status)

        self.rotate_selection_operation.status_changed.connect(self._set_status)

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

        self.marker_dock.set_data(autodrive_data)

        self.welcome_panel.hide()

        self.setWindowModified(False)
        self.actions.save_xml_action.setEnabled(True)
        self.actions.save_xml_as_action.setEnabled(True)

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
