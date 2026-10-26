import json
import os
from pathlib import Path

from autodrive_editor.i18n import tr


class ProjectFileStore:
    """Saves and loads project files (JSON). Paths to the XML, background and heightmap are stored
    relative to the project file, so projects can be moved.
    """

    FORMAT_VERSION = 1
    VALID_MAP_SCALES = (1, 2, 4, 8)

    def __init__(self, projects_directory):
        self.projects_directory = Path(projects_directory).resolve()

        self.projects_directory.mkdir(parents=True, exist_ok=True)

    def save_project(self, config_path, xml_path, background_path, map_scale, heightmap_path=None):
        config_path = Path(config_path).resolve()

        if config_path.suffix.lower() != ".json":
            config_path = config_path.with_suffix(".json")

        xml_path = self._validate_required_path(xml_path, tr("AutoDrive XML"))

        background_path = self._validate_optional_path(background_path, tr("DDS file"))

        heightmap_path = self._validate_optional_path(heightmap_path, tr("heightmap"))

        map_scale = int(map_scale)

        if map_scale not in self.VALID_MAP_SCALES:
            raise ValueError(tr("Invalid map size: {scale}", scale=map_scale))

        config_directory = config_path.parent

        project_data = {
            "format_version": self.FORMAT_VERSION,
            "autodrive_xml": self._make_relative_path(xml_path, config_directory),
            "background_dds": self._make_relative_path(background_path, config_directory),
            "map_scale": map_scale,
            "heightmap": self._make_relative_path(heightmap_path, config_directory),
        }

        config_directory.mkdir(parents=True, exist_ok=True)

        with config_path.open("w", encoding="utf-8") as config_file:
            json.dump(project_data, config_file, indent=2, ensure_ascii=False)

        return config_path

    def load_project(self, config_path):
        config_path = Path(config_path).resolve()

        if not config_path.is_file():
            raise FileNotFoundError(tr("The project file was not found: {path}", path=config_path))

        try:
            with config_path.open("r", encoding="utf-8") as config_file:
                project_data = json.load(config_file)

        except json.JSONDecodeError as ex:
            raise ValueError(tr("The JSON project file is invalid: {error}", error=ex)) from ex

        self._validate_project_data(project_data)

        config_directory = config_path.parent

        xml_path = self._resolve_relative_path(project_data["autodrive_xml"], config_directory)

        xml_path = self._validate_required_path(xml_path, tr("AutoDrive XML"))

        background_path = self._resolve_relative_path(
            project_data.get("background_dds"), config_directory
        )

        background_path = self._validate_optional_path(background_path, tr("DDS file"))

        heightmap_path = self._resolve_relative_path(
            project_data.get("heightmap"), config_directory
        )

        heightmap_path = self._validate_optional_path(heightmap_path, tr("heightmap"))

        return {
            "config_path": str(config_path),
            "autodrive_xml": str(xml_path),
            "background_dds": (str(background_path) if background_path is not None else None),
            "map_scale": int(project_data["map_scale"]),
            "heightmap": (str(heightmap_path) if heightmap_path is not None else None),
        }

    def _validate_project_data(self, project_data):
        if not isinstance(project_data, dict):
            raise ValueError(tr("The JSON file contains no valid project."))

        format_version = project_data.get("format_version")

        if format_version != self.FORMAT_VERSION:
            raise ValueError(
                tr("Unsupported project file version: {version}", version=format_version)
            )

        if not project_data.get("autodrive_xml"):
            raise ValueError(tr("The project file contains no AutoDrive XML."))

        map_scale = project_data.get("map_scale")

        if map_scale not in self.VALID_MAP_SCALES:
            raise ValueError(tr("Invalid map size: {scale}", scale=map_scale))

        self._validate_relative_config_path(project_data["autodrive_xml"], tr("AutoDrive XML"))

        self._validate_relative_config_path(project_data.get("background_dds"), tr("DDS file"))

        self._validate_relative_config_path(project_data.get("heightmap"), tr("heightmap"))

    @staticmethod
    def _validate_required_path(file_path, description):
        if not file_path:
            raise ValueError(tr("No {file} was given.", file=description))

        path = Path(file_path).resolve()

        if not path.is_file():
            raise FileNotFoundError(
                tr("The {file} was not found: {path}", file=description, path=path)
            )

        return path

    @staticmethod
    def _validate_optional_path(file_path, description):
        if not file_path:
            return None

        path = Path(file_path).resolve()

        if not path.is_file():
            raise FileNotFoundError(
                tr("The {file} was not found: {path}", file=description, path=path)
            )

        return path

    @staticmethod
    def _make_relative_path(file_path, config_directory):
        if file_path is None:
            return None

        file_path = Path(file_path).resolve()

        config_directory = Path(config_directory).resolve()

        try:
            relative_path = os.path.relpath(file_path, config_directory)

        except ValueError as ex:
            raise ValueError(
                tr("The project file and the files it refers to must be on the same drive.")
            ) from ex

        return Path(relative_path).as_posix()

    @staticmethod
    def _resolve_relative_path(stored_path, config_directory):
        if not stored_path:
            return None

        stored_path = Path(stored_path)

        if stored_path.is_absolute():
            raise ValueError(
                tr(
                    "The project file contains an absolute path, but only relative paths "
                    "are supported: {path}",
                    path=stored_path,
                )
            )

        return (Path(config_directory) / stored_path).resolve()

    @staticmethod
    def _validate_relative_config_path(stored_path, description):
        if not stored_path:
            return

        if Path(stored_path).is_absolute():
            raise ValueError(
                tr(
                    "The stored path of the {file} must be relative to the project file.",
                    file=description,
                )
            )
