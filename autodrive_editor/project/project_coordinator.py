from pathlib import Path

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import QGraphicsScene

from autodrive_editor.file_io.autodrive_xml import AutoDriveXmlReader
from autodrive_editor.file_io.project_file import ProjectFileStore
from autodrive_editor.measurement.coordinator import MeasurementCoordinator
from autodrive_editor.model.autodrive_data import AutoDriveData
from autodrive_editor.rendering.scene_renderer import SceneRenderer
from autodrive_editor.selection.selection_coordinator import SelectionCoordinator
from autodrive_editor.terrain.background_map import BackgroundMap
from autodrive_editor.terrain.heightmap import Heightmap
from autodrive_editor.ui.map_view.map_view import MapView


class ProjectCoordinator(QObject):
    """Loads XML, background, heightmap and project files and rebuilds the scene from them."""

    status_changed = Signal(str)

    debug_refresh_requested = Signal()

    map_scale_changed = Signal(int)

    heightmap_path_changed = Signal(object)

    autodrive_data_loaded = Signal(object)

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

        self.autodrive_data: AutoDriveData | None = None

        self.current_xml_path: str | None = None
        self.current_config_path: str | None = None
        self.current_heightmap_path: str | None = None

    def load_background_file(self, file_path):
        self.background_map.load(file_path)

        self.update_scene_rect()

        if self.autodrive_data is None:
            self.fit_scene_in_view()

        self.status_changed.emit("DDS-Hintergrund geladen")

        self.debug_refresh_requested.emit()

    def load_heightmap_file(self, file_path):
        heightmap_data = self.heightmap.load(file_path)

        self._set_heightmap_path(heightmap_data.file_path)

        self.selection_coordinator.refresh_info()

        self.status_changed.emit(
            f"Heightmap geladen: "
            f"{heightmap_data.width} × "
            f"{heightmap_data.height}, "
            f"{heightmap_data.format_description}"
        )

        self.debug_refresh_requested.emit()

    def remove_heightmap(self):
        self.heightmap.clear()

        self._set_heightmap_path(None)

        self.selection_coordinator.refresh_info()

        self.status_changed.emit("Heightmap entfernt")

        self.debug_refresh_requested.emit()

    def set_map_scale(self, map_scale: int, map_scale_label: str):
        self.background_map.set_map_scale(map_scale)

        self.update_scene_rect()

        self.selection_coordinator.refresh_info()

        self.map_scale_changed.emit(self.background_map.map_scale)

        self.status_changed.emit(f"Kartengröße: {map_scale_label}")

        self.debug_refresh_requested.emit()

    def load_xml_file(self, file_path):
        xml_path = Path(file_path).resolve()

        autodrive_data = AutoDriveXmlReader.load(xml_path)

        self.clear_scene_content()

        self.current_xml_path = str(xml_path)

        self.autodrive_data = autodrive_data

        self.selection_coordinator.clear()

        self.background_map.restore()

        self.scene_renderer.render(self.autodrive_data)

        self.selection_coordinator.synchronize()

        self.update_scene_rect()
        self.fit_scene_in_view()

        self.measurement_coordinator.restore_scene_items()

        self.autodrive_data_loaded.emit(self.autodrive_data)

        self.status_changed.emit(f"{len(self.autodrive_data)} Waypoints geladen")

        self.debug_refresh_requested.emit()

    def save_project_file(self, config_path) -> Path:
        if not self.current_xml_path:
            raise ValueError("Bitte zuerst eine AutoDrive-XML laden")

        saved_path = self.project_files.save_project(
            config_path=config_path,
            xml_path=self.current_xml_path,
            background_path=self.background_map.file_path,
            map_scale=self.background_map.map_scale,
            heightmap_path=self.current_heightmap_path,
        )

        self.current_config_path = str(saved_path)

        self.status_changed.emit(f"Projekt gespeichert: {saved_path.name}")

        return saved_path

    def load_project_file(self, config_path):
        project_data = self.project_files.load_project(config_path)

        self.apply_project_data(project_data)

        self.current_config_path = str(Path(config_path).resolve())

        project_name = Path(config_path).name

        status_text = f"Projekt geladen: {project_name}"

        if self.heightmap.has_heightmap():
            status_text += " mit Heightmap"

        self.status_changed.emit(status_text)

        self.debug_refresh_requested.emit()

    def apply_project_data(self, project_data: dict):
        map_scale = int(project_data["map_scale"])

        if map_scale not in self.project_files.VALID_MAP_SCALES:
            raise ValueError(f"Unbekannte Kartengröße: {map_scale}")

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

        self.load_xml_file(project_data["autodrive_xml"])

    def rebuild_scene_after_style_change(self):
        if self.autodrive_data is None:
            self.status_changed.emit("Darstellungsoptionen übernommen")

            self.debug_refresh_requested.emit()
            return

        viewport_center = self.view.viewport().rect().center()

        scene_center = self.view.mapToScene(viewport_center)

        self.clear_scene_content()

        self.background_map.restore()

        self.scene_renderer.render(self.autodrive_data)

        self.selection_coordinator.synchronize()
        self.measurement_coordinator.restore_scene_items()

        self.update_scene_rect()

        self.view.centerOn(scene_center)

        self.scene_renderer.update_visibility_for_zoom(self.view.zoom_level)

        self.scene_renderer.update_visible_scene_rect(self.view.get_visible_scene_rect())

        self.status_changed.emit("Darstellungsoptionen übernommen")

        self.debug_refresh_requested.emit()

    def clear_scene_content(self):
        self.measurement_coordinator.remove_scene_items()

        self.background_map.remove_from_scene(preserve_file_path=True)

        self.scene_renderer.reset()

        self.scene.clear()

    def update_scene_rect(self):
        scene_rect = self.scene.itemsBoundingRect()

        self.scene.setSceneRect(scene_rect)

        self.scene_renderer.update_scene_rect(scene_rect)

    def fit_scene_in_view(self):
        scene_rect = self.scene.sceneRect()

        if scene_rect.isEmpty():
            return

        self.view.fitInView(scene_rect, Qt.KeepAspectRatio)

    def _set_heightmap_path(self, file_path):
        self.current_heightmap_path = str(file_path) if file_path is not None else None

        self.heightmap_path_changed.emit(self.current_heightmap_path)
