import shutil
from dataclasses import replace
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import QGraphicsScene

from autodrive_editor.file_io.autodrive_xml import (
    AutoDriveXmlReader,
    ConfigFormat,
    ConfigSource,
)
from autodrive_editor.file_io.autodrive_xml_writer import save_config
from autodrive_editor.file_io.project_file import ProjectFileStore
from autodrive_editor.file_io.routes_index import (
    add_route,
    find_route_entry,
    mark_route_saved,
    routes_index_for,
)
from autodrive_editor.file_io.savegame_vehicles import renumber_vehicle_markers
from autodrive_editor.i18n import tr
from autodrive_editor.measurement.coordinator import MeasurementCoordinator
from autodrive_editor.model.autodrive_data import AutoDriveData
from autodrive_editor.project.autosave import AutosaveInfo, AutosaveStore
from autodrive_editor.rendering.scene_renderer import SceneRenderer
from autodrive_editor.selection.selection_coordinator import SelectionCoordinator
from autodrive_editor.terrain.background_map import BackgroundMap
from autodrive_editor.terrain.heightmap import Heightmap
from autodrive_editor.terrain.map_cache import MapCache
from autodrive_editor.ui.map_view.map_view import MapView

# Heightmap a savegame keeps next to its AutoDrive config.
SAVEGAME_HEIGHTMAP_NAME = "terrain.heightmap.png"


class ProjectCoordinator(QObject):
    """Loads XML, background, heightmap and project files and rebuilds the scene from them."""

    status_changed = Signal(str)

    debug_refresh_requested = Signal()

    map_scale_changed = Signal(int)

    heightmap_path_changed = Signal(object)

    autodrive_data_loaded = Signal(object)

    # A loaded config names a map that is not imported (AutoDrive map name).
    map_missing = Signal(str)

    def __init__(
        self,
        scene: QGraphicsScene,
        view: MapView,
        project_files: ProjectFileStore,
        background_map: BackgroundMap,
        heightmap: Heightmap,
        scene_renderer: SceneRenderer,
        selection_coordinator: SelectionCoordinator,
        measurement_coordinator: MeasurementCoordinator,
        map_cache: MapCache | None = None,
        parent=None,
    ):
        super().__init__(parent)

        self.scene = scene
        self.view = view

        self.project_files = project_files
        self.background_map = background_map
        self.heightmap = heightmap
        self.scene_renderer = scene_renderer

        self.selection_coordinator = selection_coordinator

        self.measurement_coordinator = measurement_coordinator

        # Imported maps, used to load the matching map automatically.
        self.map_cache = map_cache

        self.autodrive_data: AutoDriveData | None = None

        # Format, path and map name of the loaded data.
        self.config_source: ConfigSource | None = None
        self.current_config_path: str | None = None
        self.current_heightmap_path: str | None = None

        # Markers in the order of the file on disk, to renumber vehicle targets on save.
        self._file_markers = []

        # vehicles.xml of the loaded savegame. Only saving into that
        # savegame updates it, not saving a copy elsewhere.
        self._vehicles_path: Path | None = None

        # Files backed up as .bak in this session.
        self._backed_up_paths: set[Path] = set()

    def load_background_file(self, file_path):
        self.background_map.load(file_path)

        self.update_scene_rect()

        if self.autodrive_data is None:
            self.fit_scene_in_view()

        self.status_changed.emit(tr("DDS background loaded"))

        self.debug_refresh_requested.emit()

    def load_heightmap_file(self, file_path):
        heightmap_data = self.heightmap.load(file_path)

        self._set_heightmap_path(heightmap_data.file_path)

        self.selection_coordinator.refresh_info()

        self.status_changed.emit(
            tr(
                "Heightmap loaded: {width} × {height}, {format}",
                width=heightmap_data.width,
                height=heightmap_data.height,
                format=heightmap_data.format_description,
            )
        )

        self.debug_refresh_requested.emit()

    def remove_heightmap(self):
        self.heightmap.clear()

        self._set_heightmap_path(None)

        self.selection_coordinator.refresh_info()

        self.status_changed.emit(tr("Heightmap removed"))

        self.debug_refresh_requested.emit()

    def set_map_scale(self, map_scale: int, map_scale_label: str):
        self.background_map.set_map_scale(map_scale)

        self.update_scene_rect()

        self.selection_coordinator.refresh_info()

        self.map_scale_changed.emit(self.background_map.map_scale)

        self.status_changed.emit(tr("Map size: {size}", size=map_scale_label))

        self.debug_refresh_requested.emit()

    def load_xml_file(
        self, file_path, display_name=None, map_name=None, detect_map=True, original_path=None
    ):
        """Loads a route file or savegame config. Route files do not contain
        their map name; it comes from the caller or from routes.xml.

        With detect_map, the imported map with that name is loaded as
        background together with its heightmap and map size. Project files
        bring their own map settings and turn this off.

        original_path is set when an autosave copy is restored: the data
        then counts as loaded from that file and is saved there."""

        loaded = AutoDriveXmlReader.read(Path(file_path).resolve())

        xml_path = Path(original_path or file_path).resolve()

        source = loaded.source

        if source.format == ConfigFormat.ROUTE_EXPORT and map_name is None:
            entry = find_route_entry(xml_path)

            if entry is not None:
                map_name = entry.map_name
                display_name = display_name or entry.name

        source = replace(
            source,
            path=xml_path,
            map_name=map_name or source.map_name,
            display_name=display_name or xml_path.stem,
        )

        self.clear_scene_content()

        self.autodrive_data = loaded.data
        self.config_source = source
        self._file_markers = list(loaded.data.markers.values())
        self._vehicles_path = (
            xml_path.parent / "vehicles.xml" if source.format == ConfigFormat.SAVEGAME else None
        )

        self.selection_coordinator.clear()

        map_loaded, map_note = self._load_detected_map(source) if detect_map else (False, "")

        if not map_loaded:
            self.background_map.restore()

        self.scene_renderer.render(self.autodrive_data)

        self.selection_coordinator.synchronize()

        self.update_scene_rect()
        self.fit_scene_in_view()

        self.measurement_coordinator.restore_scene_items()

        self.autodrive_data_loaded.emit(self.autodrive_data)

        self.status_changed.emit(
            tr(
                "{format} “{name}” loaded: {count} waypoints{map_note}",
                format=source.format_label,
                name=source.display_name,
                count=len(self.autodrive_data),
                map_note=map_note,
            )
        )

        self.debug_refresh_requested.emit()

        if detect_map and not map_loaded and self._map_is_missing(source):
            self.map_missing.emit(source.map_name)

    def load_map_for_current_config(self) -> bool:
        """Loads the imported map of the current config, e.g. after it was
        imported. The nodes stay as they are."""

        if self.config_source is None:
            return False

        map_loaded, map_note = self._load_detected_map(self.config_source)

        if map_loaded:
            self.update_scene_rect()
            self.status_changed.emit(tr("Map loaded{map_note}", map_note=map_note))

        return map_loaded

    def _map_is_missing(self, source: ConfigSource) -> bool:
        return (
            self.map_cache is not None
            and bool(source.map_name)
            and self.map_cache.find(source.map_name) is None
        )

    def save_xml_file(self) -> list[str]:
        """Saves the data into the file it was loaded from. Routes listed in
        routes.xml get a new revision; in savegames the marker numbers in
        vehicles.xml are updated. Each written file is backed up as .bak
        once per session. Returns the names of vehicles whose marker was
        deleted."""

        source = self.config_source

        if source is None:
            raise ValueError(tr("Load an AutoDrive XML first"))

        self._back_up(source.path)
        save_config(self.autodrive_data, source)

        affected_vehicles = []

        if source.format == ConfigFormat.ROUTE_EXPORT:
            routes_xml_path = routes_index_for(source.path)

            if routes_xml_path.is_file():
                self._back_up(routes_xml_path)
                mark_route_saved(source.path, datetime.now())
        elif self._vehicles_path is not None:
            affected_vehicles = self._renumber_vehicle_markers(self._vehicles_path)

        self._file_markers = list(self.autodrive_data.markers.values())

        self.status_changed.emit(
            tr("{format} “{name}” saved", format=source.format_label, name=source.display_name)
        )

        return affected_vehicles

    def _renumber_vehicle_markers(self, vehicles_path: Path) -> list[str]:
        """Markers are recognised by object, so moved and renamed markers
        keep their identity."""

        positions = {
            id(marker): number
            for number, marker in enumerate(self.autodrive_data.markers.values(), start=1)
        }
        new_numbers = {
            number: positions.get(id(marker))
            for number, marker in enumerate(self._file_markers, start=1)
        }

        if not vehicles_path.is_file() or all(old == new for old, new in new_numbers.items()):
            return []

        self._back_up(vehicles_path)

        return renumber_vehicle_markers(vehicles_path, new_numbers)

    def save_as_route(self, name: str, map_name: str):
        """Saves the data as a new route in the RoutesManager the current
        route is listed in, and goes on with that route."""

        routes_xml_path = routes_index_for(self.config_source.path)
        self._back_up(routes_xml_path)
        target = add_route(routes_xml_path, name, map_name, datetime.now())

        self._save_as(target, display_name=name, map_name=map_name)

    def save_as_file(self, target: Path) -> list[str]:
        """Saves the data into another file in the same format and goes on
        with that file. Returns affected vehicles like save_xml_file."""

        target = Path(target).resolve()

        if target == self.config_source.path:
            return self.save_xml_file()

        if target.is_file():
            self._back_up(target)

        self._save_as(target, display_name=target.stem, map_name=self.config_source.map_name)

        return []

    def _save_as(self, target: Path, display_name: str, map_name: str | None):
        # The loaded file is the template, so its other settings are kept.
        shutil.copyfile(self.config_source.path, target)

        source = replace(
            self.config_source, path=target, display_name=display_name, map_name=map_name
        )
        save_config(self.autodrive_data, source)

        self.config_source = source
        self._file_markers = list(self.autodrive_data.markers.values())
        self._vehicles_path = None

        self.status_changed.emit(
            tr("{format} “{name}” saved", format=source.format_label, name=display_name)
        )

    def write_autosave(self, store: AutosaveStore):
        positions = {id(marker): number for number, marker in enumerate(self._file_markers, 1)}
        markers = self.autodrive_data.markers.values()

        store.write(
            self.autodrive_data,
            self.config_source,
            [positions.get(id(marker)) for marker in markers],
            len(self._file_markers),
        )

    def restore_autosave(self, store: AutosaveStore, info: AutosaveInfo):
        """Loads the autosaved data as if it was loaded from its original
        file, so saving writes there and still updates vehicles.xml."""

        self.load_xml_file(
            store.xml_path,
            display_name=info.display_name,
            map_name=info.map_name,
            original_path=info.source_path,
        )

        # Placeholders stand for markers deleted before the autosave.
        file_markers = [object() for _ in range(info.file_marker_count)]
        markers = self.autodrive_data.markers.values()

        for marker, number in zip(markers, info.marker_numbers, strict=False):
            if number is not None and number <= len(file_markers):
                file_markers[number - 1] = marker

        self._file_markers = file_markers

    def _back_up(self, path: Path):
        if path in self._backed_up_paths:
            return

        shutil.copy2(path, path.with_name(path.name + ".bak"))
        self._backed_up_paths.add(path)

    def save_project_file(self, config_path) -> Path:
        if self.config_source is None:
            raise ValueError(tr("Load an AutoDrive XML first"))

        saved_path = self.project_files.save_project(
            config_path=config_path,
            xml_path=str(self.config_source.path),
            background_path=self.background_map.file_path,
            map_scale=self.background_map.map_scale,
            heightmap_path=self.current_heightmap_path,
        )

        self.current_config_path = str(saved_path)

        self.status_changed.emit(tr("Project saved: {name}", name=saved_path.name))

        return saved_path

    def load_project_file(self, config_path):
        project_data = self.project_files.load_project(config_path)

        self.apply_project_data(project_data)

        self.current_config_path = str(Path(config_path).resolve())

        project_name = Path(config_path).name

        if self.heightmap.has_heightmap():
            status_text = tr("Project loaded with heightmap: {name}", name=project_name)
        else:
            status_text = tr("Project loaded: {name}", name=project_name)

        self.status_changed.emit(status_text)

        self.debug_refresh_requested.emit()

    def apply_project_data(self, project_data: dict):
        map_scale = int(project_data["map_scale"])

        if map_scale not in self.project_files.VALID_MAP_SCALES:
            raise ValueError(tr("Unknown map size: {scale}", scale=map_scale))

        self.selection_coordinator.clear()

        self.background_map.set_map_scale(map_scale)

        self.map_scale_changed.emit(map_scale)

        background_path = project_data["background_dds"]

        if background_path:
            self.background_map.load(background_path)

        else:
            self.background_map.remove_from_scene(preserve_file_path=False)

        heightmap_path = project_data["heightmap"]

        if heightmap_path:
            heightmap_data = self.heightmap.load(heightmap_path)

            self._set_heightmap_path(heightmap_data.file_path)

        else:
            self.heightmap.clear()

            self._set_heightmap_path(None)

        self.load_xml_file(project_data["autodrive_xml"], detect_map=False)

    def clear_scene_content(self):
        self.measurement_coordinator.remove_scene_items()

        self.background_map.remove_from_scene(preserve_file_path=True)

        self.scene_renderer.reset()

        self.scene.clear()

    def update_scene_rect(self):
        scene_rect = self.scene.itemsBoundingRect()

        self.scene.setSceneRect(scene_rect)

    def fit_scene_in_view(self):
        scene_rect = self.scene.sceneRect()

        if scene_rect.isEmpty():
            return

        self.view.fitInView(scene_rect, Qt.KeepAspectRatio)

    def _load_detected_map(self, source: ConfigSource) -> tuple[bool, str]:
        """Loads the imported map AutoDrive names in the source. Returns
        whether a background was loaded and a note for the status bar."""

        if self.map_cache is None or not source.map_name:
            return False, ""

        cached = self.map_cache.find(source.map_name)

        if cached is None:
            return False, (
                tr(" – map “{name}” is not imported (Map → Scan maps)", name=source.map_name)
            )

        self.background_map.set_map_scale(cached.map_scale)
        self.map_scale_changed.emit(cached.map_scale)

        self.background_map.load(str(cached.overview_path))

        # A savegame's own heightmap includes terrain changes made in game.
        heightmap_path = cached.heightmap_path
        savegame_heightmap = source.path.parent / SAVEGAME_HEIGHTMAP_NAME

        if source.format == ConfigFormat.SAVEGAME and savegame_heightmap.is_file():
            heightmap_path = savegame_heightmap

        if heightmap_path is not None:
            heightmap_data = self.heightmap.load(heightmap_path)
            self._set_heightmap_path(heightmap_data.file_path)
        else:
            self.heightmap.clear()
            self._set_heightmap_path(None)

        return True, tr(" – map “{name}”", name=cached.title)

    def _set_heightmap_path(self, file_path):
        self.current_heightmap_path = str(file_path) if file_path is not None else None

        self.heightmap_path_changed.emit(self.current_heightmap_path)
