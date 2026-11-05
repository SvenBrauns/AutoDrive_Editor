"""Small .i3d.shapes files for tests."""

import struct

from autodrive_editor.file_io.i3d_shapes import ShapesCipher

SEED = 37


def spline_data(name: str, shape_id: int, points) -> bytes:
    data = struct.pack("<i", len(name)) + name.encode("ascii")
    data += bytes(-len(data) % 4)
    data += struct.pack("<IIi", shape_id, 0, len(points))
    data += b"".join(struct.pack("<3f", *point) for point in points)
    return data + bytes(4)  # the extra bytes of version 10


def shapes_file(entities) -> bytes:
    """A shapes file encrypted in the same pieces as the reader reads them."""

    cipher = ShapesCipher(SEED)
    out = bytes([10, 0, SEED, 0]) + cipher.crypt(struct.pack("<i", len(entities)))

    for entity_type, data in entities:
        out += cipher.crypt(struct.pack("<i", entity_type))
        out += cipher.crypt(struct.pack("<i", len(data)))
        out += cipher.crypt(data)

    return out
