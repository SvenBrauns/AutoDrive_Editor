"""Finds map mods in a mods folder."""

import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from xml.etree.ElementTree import ParseError

from autodrive_editor.file_io.map_mod import MapMod, read_map_mod


@dataclass
class ScanResult:
    map_mods: list[MapMod] = field(default_factory=list)

    # Mods that could not be read, with the reason.
    skipped: list[tuple[str, str]] = field(default_factory=list)


def scan_for_map_mods(mods_directory: Path) -> ScanResult:
    """Map mods in the folder, zipped or unpacked, by name. Mods without a
    map are ignored; unreadable mods are listed as skipped."""

    result = ScanResult()

    if not Path(mods_directory).is_dir():
        return result

    for item in sorted(Path(mods_directory).iterdir(), key=lambda path: path.name.lower()):
        is_zip = item.is_file() and item.suffix.lower() == ".zip"
        is_folder = item.is_dir() and (item / "modDesc.xml").is_file()

        if not (is_zip or is_folder):
            continue

        try:
            map_mod = read_map_mod(item)
        except (zipfile.BadZipFile, ParseError, OSError, ValueError, KeyError) as ex:
            result.skipped.append((item.name, type(ex).__name__))
            continue

        if map_mod is not None:
            result.map_mods.append(map_mod)

    return result
