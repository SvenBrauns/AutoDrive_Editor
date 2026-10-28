"""Reads game and mod files by the names the game uses for them:

    data/placeables/…            game install folder
    $data/placeables/…           game install folder
    $moddir$FS25_SomeMod/xml/…   mods folder, FS25_SomeMod.zip or FS25_SomeMod\\

A name without prefix inside a mod's file is relative to that mod.
"""

from pathlib import Path

from autodrive_editor.file_io.mod_archive import ModArchive
from autodrive_editor.i18n import tr

MOD_PREFIX = "$moddir$"


def locate(name: str, mod: str | None = None) -> tuple[str | None, str]:
    """(mod, path inside it) of a file name used by the game; mod None is the
    install folder. mod is the mod the name was read from."""

    name = name.strip().replace("\\", "/")

    if name.startswith(MOD_PREFIX):
        mod, _, path = name.removeprefix(MOD_PREFIX).partition("/")
        return mod, path

    if name.startswith("$data/"):
        return None, name.removeprefix("$")

    return mod, name


class GameFiles:
    """Files of the game install folder and of the installed mods. Opened mods
    stay open until close()."""

    def __init__(self, install_directory: Path | None, mods_directory: Path | None):
        self.install_directory = install_directory
        self.mods_directory = mods_directory
        self._archives: dict[str, ModArchive] = {}

    def read(self, mod: str | None, path: str) -> bytes:
        if mod is not None:
            return self._archive(mod).read(path)

        if self.install_directory is None:
            raise FileNotFoundError(tr("The FS25 install folder is not set"))

        return (self.install_directory / path).read_bytes()

    def _archive(self, mod: str) -> ModArchive:
        if mod not in self._archives:
            if self.mods_directory is None:
                raise FileNotFoundError(tr("Mod not found: {path}", path=mod))

            zipped = self.mods_directory / f"{mod}.zip"
            self._archives[mod] = ModArchive(
                zipped if zipped.is_file() else self.mods_directory / mod
            )

        return self._archives[mod]

    def close(self):
        for archive in self._archives.values():
            archive.close()

        self._archives.clear()

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.close()
