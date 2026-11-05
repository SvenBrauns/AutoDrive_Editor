"""Spline shapes from a map's `<map>.i3d.shapes` file.

The cipher is a port of I3DShapesTool by Daniel Hultgren (Donkie), MIT license, see
THIRD_PARTY_NOTICES.md.

File: byte 0 = version (FS25: 10), byte 2 = seed, then encrypted reads. Every read starts a new
keystream at a 64-byte block counter and advances it by the blocks it used, so a mesh can be
skipped without decrypting it. Content: int32 entity count, then per entity int32 type, int32
size and the data. Type 2 is a spline: int32 name length, the name (padded to 4 bytes), uint32
shapeId, uint32 flags, int32 point count, the points (3 floats each, local to the Shape node).
"""

import struct
from typing import BinaryIO

from autodrive_editor.paths import PACKAGE_ROOT

KEY_PATH = PACKAGE_ROOT / "resources" / "i3d_shapes_key.bin"
SPLINE_ENTITY = 2
# Older versions keep version and seed at other bytes; FS25 maps use version 10.
FIRST_VERSION = 4
MASK = 0xFFFFFFFF

_keys: tuple[int, ...] = ()


class ShapesError(Exception):
    """The file is not a shapes file this reader understands."""


def _rotate(value: int, bits: int) -> int:
    return ((value << bits) | (value >> (32 - bits))) & MASK


def _keystream_block(key: list[int], counter: int) -> bytes:
    start = list(key)
    start[8], start[9] = counter & MASK, counter >> 32
    t = list(start)

    def first(a, b, c, d):
        t[c] ^= _rotate((t[b] + t[a]) & MASK, 7)
        t[d] ^= _rotate((t[c] + t[a]) & MASK, 9)
        t[b] ^= _rotate((t[c] + t[d]) & MASK, 13)
        t[a] ^= _rotate((t[b] + t[d]) & MASK, 18)

    def second(a, b, c, d):
        t[c] ^= _rotate((t[b] + t[a]) & MASK, 7)
        t[d] ^= _rotate((t[b] + t[c]) & MASK, 9)
        t[a] ^= _rotate((t[c] + t[d]) & MASK, 13)
        t[b] ^= _rotate((t[d] + t[a]) & MASK, 18)

    for _ in range(10):
        first(0, 12, 4, 8), first(5, 1, 9, 13), first(10, 6, 14, 2), first(15, 11, 3, 7)
        second(3, 0, 1, 2), second(4, 5, 6, 7), first(10, 9, 11, 8), second(14, 15, 12, 13)

    return struct.pack("<16I", *((start[i] + t[i]) & MASK for i in range(16)))


class ShapesCipher:
    """The keystream of one file. Encrypting and decrypting are the same operation, as long as
    the data is passed in the same pieces as the reads."""

    def __init__(self, seed: int):
        global _keys

        if not _keys:
            data = KEY_PATH.read_bytes()
            _keys = struct.unpack(f"<{len(data) // 4}I", data)

        self.key = list(_keys[seed * 16 : seed * 16 + 16])
        self.block = 0

    def crypt(self, data: bytes) -> bytes:
        blocks = -(-len(data) // 64)
        stream = b"".join(_keystream_block(self.key, self.block + i) for i in range(blocks))
        self.block += blocks
        size = len(data)
        return (int.from_bytes(data, "little") ^ int.from_bytes(stream[:size], "little")).to_bytes(
            size, "little"
        )

    def skip(self, size: int) -> None:
        self.block += -(-size // 64)


def read_splines(stream: BinaryIO) -> dict[int, list[tuple[float, float, float]]]:
    """The local points of every spline in the shapes file, by shapeId. Meshes are skipped
    (stream.seek), so a zip member can be read without loading it whole."""

    header = stream.read(4)

    if len(header) < 4 or header[0] < FIRST_VERSION:
        raise ShapesError("Not a shapes file of a supported version")

    cipher = ShapesCipher(header[2])

    def read(size: int) -> bytes:
        data = stream.read(size)

        if len(data) < size:
            raise ShapesError("The shapes file ends early")

        return cipher.crypt(data)

    def int32() -> int:
        return struct.unpack("<i", read(4))[0]

    splines = {}

    for _ in range(int32()):
        entity_type, size = int32(), int32()

        if entity_type != SPLINE_ENTITY:
            stream.seek(size, 1)
            cipher.skip(size)
            continue

        data = read(size)

        try:
            name_length = struct.unpack_from("<i", data)[0]
            offset = 4 + name_length
            offset += -offset % 4
            shape_id, _flags, count = struct.unpack_from("<IIi", data, offset)
            points = list(struct.iter_unpack("<3f", data[offset + 12 : offset + 12 + 12 * count]))
        except struct.error as error:
            raise ShapesError("Broken spline entry") from error

        if len(points) != count:
            raise ShapesError("Broken spline entry")

        splines[shape_id] = points

    return splines
