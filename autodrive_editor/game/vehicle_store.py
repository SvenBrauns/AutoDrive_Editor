"""Shop name and picture of a vehicle, from its vehicle XML in the game folder or a mod.

Vehicle files are named as in vehicles.xml: `data/vehicles/…/x.xml` (game install folder) or
`$moddir$<mod>/…/x.xml` (mods folder, a zip or a folder). The XML's `<storeData>` holds the
name and the picture (`store_x.png`, on disk as `store_x.dds`). DLC files are encrypted and
give nothing.
"""

import io
import re
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path, PurePosixPath

from PIL import Image

_MODDIR = re.compile(r"^\$moddir\$([^/]+)/(.+)$")


@dataclass(frozen=True)
class StoreInfo:
    name: str
    image: Image.Image | None


@lru_cache(maxsize=256)
def store_info(filename: str, install_path: Path | None, mods_path: Path | None) -> StoreInfo:
    """Name and picture of the vehicle; empty name and no picture if its files are not found."""

    xml_bytes = _read(filename, install_path, mods_path)

    try:
        store = ET.fromstring(xml_bytes).find("storeData") if xml_bytes else None
    except ET.ParseError:
        store = None

    if store is None:
        return StoreInfo("", None)

    image = None
    image_name = (store.findtext("image") or "").strip()

    if image_name:
        if not image_name.startswith("$"):
            image_name = str(PurePosixPath(filename).parent / image_name)

        image = _image(
            _read(str(PurePosixPath(image_name).with_suffix(".dds")), install_path, mods_path)
        )

    return StoreInfo(_name(store.find("name")), image)


def _name(element: ET.Element | None) -> str:
    if element is None:
        return ""

    text = (element.text or "").strip() or (element.findtext("en") or "").strip()
    return "" if text.startswith("$l10n") else text


def _image(data: bytes | None) -> Image.Image | None:
    if not data:
        return None

    try:
        return Image.open(io.BytesIO(data)).convert("RGBA")
    except Exception:
        return None


def _read(filename: str, install_path: Path | None, mods_path: Path | None) -> bytes | None:
    """The bytes of a game file, None if it is not found."""

    filename = filename.replace("\\", "/")
    mod = _MODDIR.match(filename)

    try:
        if mod is not None:
            return _read_mod_file(mods_path, mod.group(1), mod.group(2))

        relative = filename.removeprefix("$")

        if relative.startswith("data/") and install_path is not None:
            return (install_path / relative).read_bytes()
    except (OSError, KeyError, zipfile.BadZipFile):
        pass

    return None


def _read_mod_file(mods_path: Path | None, mod: str, member: str) -> bytes | None:
    if mods_path is None:
        return None

    folder = mods_path / mod

    if folder.is_dir():
        return (folder / member).read_bytes()

    with zipfile.ZipFile(mods_path / f"{mod}.zip") as archive:
        return archive.read(member)
