"""Automatic backup copies of unsaved edits, kept in the editor's own data
folder (never in the game folder).

There is one slot: autosave.xml holds the data in the format of the
loaded file, autosave.json where it came from. If the editor ends without
saving or discarding the edits, the next start offers to restore them.
"""

import json
import shutil
from dataclasses import asdict, dataclass, replace
from datetime import datetime
from pathlib import Path

from autodrive_editor.file_io.autodrive_xml import ConfigFormat, ConfigSource
from autodrive_editor.file_io.autodrive_xml_writer import save_config
from autodrive_editor.model.autodrive_data import AutoDriveData


@dataclass(frozen=True)
class AutosaveInfo:
    """Where the autosaved data came from.

    marker_numbers holds, for each marker in order, its number in the
    original file (None for new markers), so vehicle targets can still be
    renumbered when the restored data is saved into a savegame."""

    source_path: str
    format: str
    display_name: str | None
    map_name: str | None
    saved_at: str
    marker_numbers: list[int | None]
    file_marker_count: int

    @property
    def config_format(self) -> ConfigFormat:
        return ConfigFormat(self.format)


class AutosaveStore:
    def __init__(self, directory: Path):
        self.directory = Path(directory)
        self.xml_path = self.directory / "autosave.xml"
        self.info_path = self.directory / "autosave.json"

    def write(self, data: AutoDriveData, source: ConfigSource, marker_numbers, file_marker_count):
        """The loaded file is copied first, so settings in it (e.g. of a
        savegame config) are kept in the copy."""

        self.directory.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source.path, self.xml_path)
        save_config(data, replace(source, path=self.xml_path))

        info = AutosaveInfo(
            source_path=str(source.path),
            format=source.format.value,
            display_name=source.display_name,
            map_name=source.map_name,
            saved_at=datetime.now().strftime("%d.%m.%Y %H:%M"),
            marker_numbers=list(marker_numbers),
            file_marker_count=file_marker_count,
        )
        self.info_path.write_text(json.dumps(asdict(info), indent=2), encoding="utf-8")

    def read(self) -> AutosaveInfo | None:
        if not self.xml_path.is_file() or not self.info_path.is_file():
            return None

        try:
            return AutosaveInfo(**json.loads(self.info_path.read_text(encoding="utf-8")))
        except (ValueError, TypeError):
            return None

    def clear(self):
        self.xml_path.unlink(missing_ok=True)
        self.info_path.unlink(missing_ok=True)
