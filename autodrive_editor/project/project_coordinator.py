import logging
import shutil
from collections.abc import Callable
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
from autodrive_editor.file_io.autodrive_xml_writer import save_config, write_route_export
from autodrive_editor.file_io.disk_state import DiskState, file_stamp, network_fingerprint
from autodrive_editor.file_io.game_files import GameFiles
from autodrive_editor.file_io.navigation_costmap import CostmapError, costmap_path, read_costmap
from autodrive_editor.file_io.routes_index import (
    add_route,
    create_routes_index,
    find_route_entry,
    mark_route_saved,
    read_routes_index,
    routes_index_for,
)
from autodrive_editor.file_io.savegame_buildings import SavegameBuildings, read_savegame_buildings
from autodrive_editor.file_io.savegame_vehicles import (
    read_park_destinations,
    renumber_vehicle_markers,
)
from autodrive_editor.i18n import tr
from autodrive_editor.measurement.coordinator import MeasurementCoordinator
from autodrive_editor.model.autodrive_data import AutoDriveData, MarkerData
from autodrive_editor.project.autosave import AutosaveInfo, AutosaveStore
from autodrive_editor.rendering.scene_renderer import SceneRenderer
from autodrive_editor.selection.selection_coordinator import SelectionCoordinator
from autodrive_editor.terrain.background_map import BackgroundMap, map_scale_for_extent
from autodrive_editor.terrain.game_picture import find_picture, savegame_key
from autodrive_editor.terrain.heightmap import Heightmap
from autodrive_editor.terrain.map_cache import MapCache
from autodrive_editor.ui.map_view.map_view import MapView

logger = logging.getLogger(__name__)

# Heightmap a savegame keeps next to its AutoDrive config.
SAVEGAME_HEIGHTMAP_NAME = "terrain.heightmap.png"


class ProjectCoordinator(QObject):
    """Loads XML, background and heightmap and rebuilds the scene from them."""

    status_changed = Signal(str)

    debug_refresh_requested = Signal()

    # The backgrounds the loaded map has (ground map, game picture) changed.
    backgrounds_changed = Signal()

    autodrive_data_loaded = Signal(object)

    def __init__(
        self,
        scene: QGraphicsScene,
        view: MapView,
        background_map: BackgroundMap,
        heightmap: Heightmap,
        scene_renderer: SceneRenderer,
        selection_coordinator: SelectionCoordinator,
        measurement_coordinator: MeasurementCoordinator,
        map_cache: MapCache | None = None,
        game_files: Callable[[], GameFiles] | None = None,
        parent=None,
    ):
        super().__init__(parent)

        self.scene = scene
        self.view = view

        self.background_map = background_map
        self.heightmap = heightmap
        self.scene_renderer = scene_renderer

        self.selection_coordinator = selection_coordinator

        self.measurement_coordinator = measurement_coordinator

        # Imported maps, used to load the matching map automatically.
        self.map_cache = map_cache

        # Opens the game and mod files the savegame's buildings are read from.
        self.game_files = game_files

        # The map chosen for a file under Settings → Maps (AutoDrive name), None if none.
        self.map_for_file: Callable[[Path], str | None] = lambda path: None

        # Called with the source of a file about to be shown; imports its map if it is missing.
        self.prepare_map: Callable[[ConfigSource], None] = lambda source: None

        self.autodrive_data: AutoDriveData | None = None

        # Format, path and map name of the loaded data.
        self.config_source: ConfigSource | None = None
        self.current_heightmap_path: str | None = None

        # Markers in the order of the file on disk, to renumber vehicle targets on save.
        self._file_markers = []

        # vehicles.xml of the loaded savegame. Only saving into that
        # savegame updates it, not saving a copy elsewhere.
        self._vehicles_path: Path | None = None

        # Status bar note about buildings that could not be read.
        self.buildings_note = ""
        # The savegame the drivability map was looked for in.
        self.costmap_directory: Path | None = None

        # Files backed up as .bak in this session.
        self._backed_up_paths: set[Path] = set()

        # The open file as last read or written, to notice changes by the game.
        self._disk_state: DiskState | None = None

    def load_xml_file(self, file_path, display_name=None, map_name=None, original_path=None):
        """Loads a route file or savegame config. Route files do not contain
        their map name; it comes from the caller or from routes.xml. The
        imported map with that name is loaded as background together with
        its heightmap and map size.

        original_path is set when an autosave copy is restored: the data
        then counts as loaded from that file and is saved there."""

        stamp = file_stamp(Path(file_path))
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
            map_name=self.map_for_file(xml_path) or map_name or source.map_name,
            display_name=display_name or xml_path.stem,
        )

        self.prepare_map(source)
        self._show_loaded(loaded.data, source)

        if original_path is None:
            self._disk_state = DiskState(stamp, network_fingerprint(loaded.data, source.format))
        else:
            # A restored autosave: the original file counts as it is now.
            self._disk_state = self._state_on_disk()

    def reload_file(self):
        """Loads the open file again from disk. The view keeps its position and zoom."""

        source = self.config_source
        transform = self.view.transform()
        center = self.view.mapToScene(self.view.viewport().rect().center())

        self.load_xml_file(source.path, display_name=source.display_name, map_name=source.map_name)

        self.view.setTransform(transform)
        self.view.centerOn(center)

    def file_changed_on_disk(self) -> bool:
        """Whether someone else (usually the game) changed the network in the open file since
        the editor opened or saved it. A file that cannot be read counts as changed, a file that
        is gone does not."""

        state, source = self._disk_state, self.config_source

        if state is None or source is None:
            return False

        stamp = file_stamp(source.path)

        if stamp is None or stamp == state.stamp:
            return False

        try:
            on_disk = self._state_on_disk()
        except Exception:
            return True

        if on_disk.fingerprint != state.fingerprint:
            return True

        # Rewritten with the same network, e.g. by a save of the game.
        self._disk_state = on_disk
        return False

    def _remember_disk_state(self):
        source = self.config_source
        fingerprint = network_fingerprint(self.autodrive_data, source.format)
        self._disk_state = DiskState(file_stamp(source.path), fingerprint)

    def _state_on_disk(self) -> DiskState:
        source = self.config_source
        stamp = file_stamp(source.path)
        data = AutoDriveXmlReader.read(source.path).data

        return DiskState(stamp, network_fingerprint(data, source.format))

    def start_empty_savegame(self, config_path, display_name: str, map_name: str):
        """Opens a savegame that has no AutoDrive data yet with an empty network. Save creates
        its AutoDrive_config.xml."""

        source = ConfigSource(
            ConfigFormat.SAVEGAME,
            Path(config_path).resolve(),
            map_name=self.map_for_file(config_path) or map_name or None,
            display_name=display_name,
        )
        self.prepare_map(source)
        self._show_loaded(AutoDriveData(), source)
        self._remember_disk_state()

    def _show_loaded(self, data: AutoDriveData, source: ConfigSource):
        xml_path = source.path

        self.clear_scene_content()

        self.autodrive_data = data
        self.config_source = source
        self._file_markers = list(data.markers.values())
        self._vehicles_path = (
            xml_path.parent / "vehicles.xml" if source.format == ConfigFormat.SAVEGAME else None
        )

        self.selection_coordinator.clear()

        map_loaded, map_note = self._load_detected_map(source)

        if not map_loaded:
            self._show_without_map(data)

        self.scene_renderer.render(self.autodrive_data)
        self.show_parking()
        self._show_buildings()

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
                map_note=map_note + self.buildings_note,
            )
        )

        self.debug_refresh_requested.emit()

    def use_map(self, map_name: str):
        """Shows the open file on another imported map (Settings → Maps)."""

        self.config_source = replace(self.config_source, map_name=map_name)
        self.load_map_for_current_config()

    def unload_map(self):
        """Takes the map from under the open file, e.g. before the map is removed."""

        if self.autodrive_data is not None:
            self._show_without_map(self.autodrive_data)
            self.update_scene_rect()

    def _show_without_map(self, data: AutoDriveData):
        """No imported map: no background and heightmap; the map size is the network's extent."""

        self.background_map.remove_from_scene(preserve_file_path=False)
        self.backgrounds_changed.emit()
        self.heightmap.clear()
        self._set_heightmap_path(None)

        nodes = data.nodes.values()
        map_scale = map_scale_for_extent([n.x for n in nodes], [n.z for n in nodes])
        self.background_map.set_map_scale(map_scale)

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
        self._remember_disk_state()

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
        new_numbers = self._marker_numbers()

        if not vehicles_path.is_file() or all(old == new for old, new in new_numbers.items()):
            return []

        self._back_up(vehicles_path)

        return renumber_vehicle_markers(vehicles_path, new_numbers)

    def _marker_numbers(self) -> dict[int, int | None]:
        """Number in the file on disk → number now (None: deleted). Markers are recognised by
        object, so moved and renamed markers keep their identity. A marker that is gone, e.g.
        after Load route into savegame, is matched by name and group if exactly one marker has
        them."""

        markers = list(self.autodrive_data.markers.values())
        positions = {id(marker): number for number, marker in enumerate(markers, start=1)}
        by_key: dict[tuple[str, str], list[int]] = {}

        for number, marker in enumerate(markers, start=1):
            by_key.setdefault((marker.name, marker.group), []).append(number)

        numbers = {}

        for number, marker in enumerate(self._file_markers, start=1):
            new = positions.get(id(marker))

            # Placeholders of an autosave stand for markers deleted before it.
            if new is None and isinstance(marker, MarkerData):
                matches = by_key.get((marker.name, marker.group), [])
                new = matches[0] if len(matches) == 1 else None

            numbers[number] = new

        return numbers

    def save_as_route(self, name: str, routes_xml_path: Path) -> Path:
        """Writes the network as a route of the RoutesManager; a route of the same name is
        replaced and gets a new revision. A savegame stays open (the route keeps a version of
        it); a route or other file goes on as the saved route. Returns the route file."""

        source = self.config_source
        map_name = source.map_name or ""
        now = datetime.now()

        if not routes_xml_path.is_file():
            create_routes_index(routes_xml_path)

        self._back_up(routes_xml_path)
        entry = next((e for e in read_routes_index(routes_xml_path) if e.name == name), None)

        if entry is not None:
            target = entry.path
            self._back_up(target)
            mark_route_saved(target, now)
        else:
            target = add_route(routes_xml_path, name, map_name, now)
            target.parent.mkdir(parents=True, exist_ok=True)

        write_route_export(self.autodrive_data, target)

        if source.format != ConfigFormat.SAVEGAME:
            self.config_source = replace(
                source, format=ConfigFormat.ROUTE_EXPORT, path=target, display_name=name
            )
            self._file_markers = list(self.autodrive_data.markers.values())
            self._vehicles_path = None
            self._remember_disk_state()

        self.status_changed.emit(tr("Route “{name}” saved", name=name))

        return target

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
        self.show_parking()

    def show_parking(self):
        """Marks the markers the vehicles of the loaded savegame park at, numbered in the order
        of the file on disk. After the network was replaced the matching new markers are marked
        too; only markers in the network are drawn."""

        numbers = set()

        if self._vehicles_path is not None and self._vehicles_path.is_file():
            numbers = read_park_destinations(self._vehicles_path)

        markers = list(self.autodrive_data.markers.values()) if self.autodrive_data else []
        now = self._marker_numbers() if self.autodrive_data else {}
        parked = [m for number, m in enumerate(self._file_markers, start=1) if number in numbers]
        parked += [markers[now[number] - 1] for number in numbers if now.get(number)]
        self.scene_renderer.set_parking_markers({id(m): m for m in parked}.values())

    def _show_buildings(self):
        """Shows the sheds and stations of the buildings in the loaded savegame."""

        directory = self.savegame_folder()

        buildings = SavegameBuildings()

        if directory is not None and self.game_files is not None:
            with self.game_files() as files:
                buildings = read_savegame_buildings(directory, files)

        self.scene_renderer.set_buildings(buildings)
        self._show_costmap(directory)
        failed = buildings.failed
        self.buildings_note = (
            tr(" – {count} buildings could not be read (see log file)", count=len(failed))
            if failed
            else ""
        )

    def _show_costmap(self, directory: Path | None):
        """Reads the drivability map of the savegame, if it has one (see navigation_costmap)."""

        self.costmap_directory = directory
        costmap = None

        if directory is not None and costmap_path(directory).is_file():
            try:
                costmap = read_costmap(costmap_path(directory))
            except (OSError, CostmapError) as error:
                logger.warning("The drivability map could not be read: %s", error)

        self.scene_renderer.set_costmap(costmap)

    def _back_up(self, path: Path):
        if path in self._backed_up_paths or not path.is_file():
            return

        shutil.copy2(path, path.with_name(path.name + ".bak"))
        self._backed_up_paths.add(path)

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

        if self.map_cache is None:
            return False, ""

        if not source.map_name:
            return False, tr(
                " – no map known; choose one under File → Settings → Maps → "
                "“Use this map for the open file”"
            )

        cached = self.map_cache.find(source.map_name)

        if cached is None:
            return False, (
                tr(" – map “{name}” is not imported (File → Settings → Maps)", name=source.map_name)
            )

        self.background_map.set_map_scale(cached.map_scale)

        self.background_map.load(str(cached.overview_path))
        self.background_map.set_ground(cached.ground_path, cached.fields())
        self._load_map_picture(source, cached)

        self._load_map_heightmap(source, cached)

        return True, tr(" – map “{name}”", name=cached.title)

    def _load_map_heightmap(self, source: ConfigSource, cached):
        """Loads the heightmap of the loaded savegame, else the map's dem.png.
        A savegame's own heightmap includes terrain changes made in game."""

        heightmap_path = cached.heightmap_path
        savegame = self._savegame_folder(source)

        if savegame is not None and (savegame / SAVEGAME_HEIGHTMAP_NAME).is_file():
            heightmap_path = savegame / SAVEGAME_HEIGHTMAP_NAME

        if heightmap_path is not None:
            heightmap_data = self.heightmap.load(heightmap_path)
            self._set_heightmap_path(heightmap_data.file_path)
        else:
            self.heightmap.clear()
            self._set_heightmap_path(None)

    def _load_map_picture(self, source: ConfigSource, cached):
        """The game picture of the loaded savegame, else the map's newest one."""

        savegame = savegame_key(self._savegame_folder(source))
        self.background_map.set_picture(find_picture(cached.directory, savegame))
        self.backgrounds_changed.emit()

    def loaded_map(self):
        """The imported map of the loaded config; None if it has none."""

        source = self.config_source

        if self.map_cache is None or source is None or not source.map_name:
            return None

        return self.map_cache.find(source.map_name)

    def savegame_folder(self) -> Path | None:
        """The savegame the loaded config belongs to; None for a route."""

        return self._savegame_folder(self.config_source) if self.config_source else None

    @staticmethod
    def _savegame_folder(source: ConfigSource) -> Path | None:
        return source.path.parent if source.format == ConfigFormat.SAVEGAME else None

    def _set_heightmap_path(self, file_path):
        self.current_heightmap_path = str(file_path) if file_path is not None else None
