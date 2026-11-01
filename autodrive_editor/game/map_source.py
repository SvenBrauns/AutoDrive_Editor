"""Finds the mod a map comes from, to import a missing map without asking.

A savegame names its map in careerSavegame.xml: `FS25_Thueringen_2_0_16x.SampleModMap` is map
`SampleModMap` of the mod `FS25_Thueringen_2_0_16x` (zip or folder in mods/); an id without a dot
is a base game map. A route only has the AutoDrive map name from routes.xml, so the mods are
scanned for a map with that name.
"""

import zipfile
from pathlib import Path
from xml.etree.ElementTree import ParseError

from autodrive_editor.file_io.base_game_maps import BASE_GAME_MOD_NAME
from autodrive_editor.file_io.map_mod import MapEntry, MapMod, read_map_mod
from autodrive_editor.game.map_scanner import scan_for_map_mods
from autodrive_editor.terrain.map_cache import CachedMap

MapSource = tuple[MapMod, MapEntry]

READ_ERRORS = (zipfile.BadZipFile, ParseError, OSError, ValueError, KeyError)


def split_map_id(map_id: str) -> tuple[str | None, str]:
    """(mod name, map id inside the mod); the mod name is None for a base game map."""

    mod_name, dot, inner_id = map_id.partition(".")

    return (mod_name, inner_id) if dot else (None, map_id)


def find_by_map_id(
    map_id: str, mods_directory: Path | None, base_maps: MapMod | None
) -> MapSource | None:
    """The map a savegame's mapId names."""

    mod_name, inner_id = split_map_id(map_id)

    if mod_name is None:
        return _entry_with_id(base_maps, inner_id)

    return _entry_with_id(_read_mod(mod_name, mods_directory), inner_id)


def find_import_source(
    cached: CachedMap, mods_directory: Path | None, base_maps: MapMod | None
) -> MapSource | None:
    """The mod and map an imported map came from, to import it again."""

    mod = base_maps if cached.mod_name == BASE_GAME_MOD_NAME else None
    mod = mod or _read_mod(cached.mod_name, mods_directory)

    if mod is None:
        return None

    return next(
        ((mod, entry) for entry in mod.maps if entry.config_file == cached.config_file), None
    )


def _read_mod(mod_name: str, mods_directory: Path | None) -> MapMod | None:
    """The mod zip or folder of this name in the mods folder; None if missing or unreadable."""

    if mods_directory is None:
        return None

    for path in (Path(mods_directory) / f"{mod_name}.zip", Path(mods_directory) / mod_name):
        if path.exists():
            try:
                return read_map_mod(path)
            except READ_ERRORS:
                return None

    return None


def find_by_map_name(
    map_name: str, mods_directory: Path | None, base_maps: MapMod | None
) -> MapSource | None:
    """The first map, base game first, that AutoDrive calls map_name."""

    mods = [base_maps] if base_maps is not None else []

    if mods_directory is not None:
        mods += scan_for_map_mods(mods_directory).map_mods

    return next(
        ((mod, entry) for mod in mods for entry in mod.maps if map_name in entry.autodrive_names),
        None,
    )


def _entry_with_id(mod: MapMod | None, map_id: str) -> MapSource | None:
    if mod is None:
        return None

    # Base game ids differ in case: the savegame says MapUS, the folder is mapUS.
    return next(
        ((mod, entry) for entry in mod.maps if entry.map_id.casefold() == map_id.casefold()), None
    )
