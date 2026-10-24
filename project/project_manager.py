import json
from pathlib import Path


class ProjectManager:

    FORMAT_VERSION = 1
    VALID_MAP_SCALES = (1, 2, 4, 8)

    def __init__(self, config_directory):
        self.config_directory = Path(
            config_directory
        ).resolve()

        self.config_directory.mkdir(
            parents=True,
            exist_ok=True
        )

    def save_project(
        self,
        config_path,
        xml_path,
        background_path,
        map_scale,
        heightmap_path=None
    ):
        config_path = Path(
            config_path
        ).resolve()

        if config_path.suffix.lower() != ".json":
            config_path = config_path.with_suffix(
                ".json"
            )

        if not xml_path:
            raise ValueError(
                "Es wurde keine AutoDrive-XML geladen."
            )

        xml_path = Path(
            xml_path
        ).resolve()

        if not xml_path.is_file():
            raise FileNotFoundError(
                f"Die AutoDrive-XML wurde nicht gefunden: "
                f"{xml_path}"
            )

        background_value = self._prepare_optional_path(
            background_path,
            "DDS-Datei"
        )

        heightmap_value = self._prepare_optional_path(
            heightmap_path,
            "Heightmap"
        )

        map_scale = int(
            map_scale
        )

        if map_scale not in self.VALID_MAP_SCALES:
            raise ValueError(
                f"Ungültige Kartengröße: {map_scale}"
            )

        project_data = {
            "format_version": self.FORMAT_VERSION,
            "autodrive_xml": str(xml_path),
            "background_dds": background_value,
            "map_scale": map_scale,
            "heightmap": heightmap_value
        }

        config_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        with config_path.open(
            "w",
            encoding="utf-8"
        ) as config_file:
            json.dump(
                project_data,
                config_file,
                indent=2,
                ensure_ascii=False
            )

        return config_path

    def load_project(self, config_path):
        config_path = Path(
            config_path
        ).resolve()

        if not config_path.is_file():
            raise FileNotFoundError(
                f"Die Projektkonfiguration wurde nicht gefunden: "
                f"{config_path}"
            )

        with config_path.open(
            "r",
            encoding="utf-8"
        ) as config_file:
            project_data = json.load(
                config_file
            )

        self._validate_project_data(
            project_data
        )

        xml_path = Path(
            project_data["autodrive_xml"]
        ).resolve()

        if not xml_path.is_file():
            raise FileNotFoundError(
                f"Die AutoDrive-XML wurde nicht gefunden: "
                f"{xml_path}"
            )

        background_path = self._validate_optional_path(
            project_data.get("background_dds"),
            "DDS-Datei"
        )

        heightmap_path = self._validate_optional_path(
            project_data.get("heightmap"),
            "Heightmap"
        )

        return {
            "config_path": str(config_path),
            "autodrive_xml": str(xml_path),
            "background_dds": background_path,
            "map_scale": int(
                project_data["map_scale"]
            ),
            "heightmap": heightmap_path
        }

    def _validate_project_data(
        self,
        project_data
    ):
        if not isinstance(
            project_data,
            dict
        ):
            raise ValueError(
                "Die JSON-Datei enthält keine gültige "
                "Projektkonfiguration."
            )

        format_version = project_data.get(
            "format_version"
        )

        if format_version != self.FORMAT_VERSION:
            raise ValueError(
                f"Nicht unterstützte Config-Version: "
                f"{format_version}"
            )

        if not project_data.get(
            "autodrive_xml"
        ):
            raise ValueError(
                "Die Projektkonfiguration enthält keine "
                "AutoDrive-XML."
            )

        map_scale = project_data.get(
            "map_scale"
        )

        if map_scale not in self.VALID_MAP_SCALES:
            raise ValueError(
                f"Ungültige Kartengröße: {map_scale}"
            )

    @staticmethod
    def _prepare_optional_path(
        file_path,
        description
    ):
        if not file_path:
            return None

        path = Path(
            file_path
        ).resolve()

        if not path.is_file():
            raise FileNotFoundError(
                f"Die {description} wurde nicht gefunden: "
                f"{path}"
            )

        return str(path)

    @staticmethod
    def _validate_optional_path(
        file_path,
        description
    ):
        if not file_path:
            return None

        path = Path(
            file_path
        ).resolve()

        if not path.is_file():
            raise FileNotFoundError(
                f"Die {description} wurde nicht gefunden: "
                f"{path}"
            )

        return str(path)