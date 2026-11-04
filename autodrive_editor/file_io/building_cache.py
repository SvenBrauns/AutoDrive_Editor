"""What the editor read from the game and mod files about buildings, kept between sessions:
the map's own buildings from the map scene (1.4 s on Thüringen) and the building definitions.

An entry is used while the file it was read from has the same size and modification time (for a
zipped mod those of the zip). The file can be deleted; it is written again.
"""

import os
import pickle
from collections.abc import Callable, Hashable
from pathlib import Path

from autodrive_editor.error_log import logger

# Raise when a reader returns something else, so entries of older editor versions are not used.
VERSION = 2


class BuildingCache:
    """Without a path the entries are kept only while the object lives."""

    def __init__(self, path: Path | None = None):
        self.path = path
        self._entries: dict[Hashable, tuple] = self._load()
        self._changed = False

    def get(self, key: Hashable, stamp: tuple | None, read: Callable[[], object]):
        """read()'s result, kept for key while stamp stays the same. Not kept if stamp is None
        or read() raises."""

        entry = self._entries.get(key)

        if stamp is not None and entry is not None and entry[0] == stamp:
            return entry[1]

        value = read()

        if stamp is not None:
            self._entries[key] = (stamp, value)
            self._changed = True

        return value

    def save(self):
        """Writes the entries if they changed. A failure is only logged: the files are read
        again next time."""

        if self.path is None or not self._changed:
            return

        temporary = self.path.with_name(self.path.name + ".tmp")

        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary.write_bytes(pickle.dumps({"version": VERSION, "entries": self._entries}))
            os.replace(temporary, self.path)
        except OSError as error:
            logger.warning("The building cache could not be written: %s", error)
            return

        self._changed = False

    def _load(self) -> dict:
        if self.path is None or not self.path.is_file():
            return {}

        try:
            content = pickle.loads(self.path.read_bytes())
        except Exception as error:
            logger.warning("The building cache could not be read: %s", error)
            return {}

        if not isinstance(content, dict) or content.get("version") != VERSION:
            return {}

        return content["entries"]
