"""Read access to the files of a mod, whether zipped or unpacked."""

import zipfile
from pathlib import Path, PurePosixPath
from typing import IO

from autodrive_editor.i18n import tr


class ModArchive:
    """Files of a mod by their path inside the mod, e.g. "maps/map.xml".
    Paths use "/" and are matched case-insensitively, like the game."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._zip: zipfile.ZipFile | None = None

        if self.path.is_file():
            self._zip = zipfile.ZipFile(self.path)
            names = self._zip.namelist()
        elif self.path.is_dir():
            names = [
                file.relative_to(self.path).as_posix()
                for file in self.path.rglob("*")
                if file.is_file()
            ]
        else:
            raise FileNotFoundError(tr("Mod not found: {path}", path=self.path))

        self._names = {name.lower(): name for name in names}

    @property
    def name(self) -> str:
        """The mod name, e.g. FS25_Thueringen_2_0_16x."""

        return self.path.stem if self.path.is_file() else self.path.name

    def close(self):
        if self._zip is not None:
            self._zip.close()
            self._zip = None

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.close()

    def resolve(self, name: str) -> str | None:
        """The real spelling of a path inside the mod, or None."""

        normalized = str(PurePosixPath(name.replace("\\", "/")))

        return self._names.get(normalized.lower())

    def exists(self, name: str) -> bool:
        return self.resolve(name) is not None

    def read(self, name: str) -> bytes:
        with self.open(name) as stream:
            return stream.read()

    def open(self, name: str) -> IO[bytes]:
        real_name = self.resolve(name)

        if real_name is None:
            raise FileNotFoundError(
                tr("{file} is missing in the mod {mod}", file=name, mod=self.name)
            )

        if self._zip is not None:
            return self._zip.open(real_name)

        return (self.path / real_name).open("rb")
