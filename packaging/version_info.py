"""Writes the Windows version info of the exe (PyInstaller --version-file) from pyproject.toml.

Usage: python packaging/version_info.py build/version_info.txt
"""

import sys
import tomllib
from pathlib import Path

PYPROJECT_PATH = Path(__file__).parents[1] / "pyproject.toml"


def version_info_text(version: str) -> str:
    numbers = (*(int(part) for part in version.split(".")), 0)
    return f"""VSVersionInfo(
  ffi=FixedFileInfo(filevers={numbers}, prodvers={numbers}),
  kids=[
    StringFileInfo([StringTable('040904B0', [
      StringStruct('FileDescription', 'AutoDrive FS25 Editor'),
      StringStruct('FileVersion', '{version}'),
      StringStruct('InternalName', 'AutoDrive Editor'),
      StringStruct('LegalCopyright', 'Sven Brauns, GPL-3.0-or-later'),
      StringStruct('OriginalFilename', 'AutoDrive Editor.exe'),
      StringStruct('ProductName', 'AutoDrive FS25 Editor'),
      StringStruct('ProductVersion', '{version}'),
    ])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])]),
  ],
)
"""


def write_version_info(path: Path):
    with open(PYPROJECT_PATH, "rb") as file:
        version = tomllib.load(file)["project"]["version"]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(version_info_text(version), encoding="utf-8")


if __name__ == "__main__":
    write_version_info(Path(sys.argv[1]))
