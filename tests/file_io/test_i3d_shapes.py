import io
import struct

import pytest

from autodrive_editor.file_io.i3d_shapes import ShapesCipher, ShapesError, read_splines

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


def test_splines_are_read_back_and_meshes_skipped():
    first = [(1.0, 2.0, 3.0), (4.5, -6.0, 7.25)]
    second = [(float(i), 0.0, -float(i)) for i in range(30)]
    data = shapes_file(
        [
            (1, bytes(range(200))),
            (2, spline_data("lane", 5, first)),
            (6, bytes(70)),
            (2, spline_data("lane02", 9, second)),
        ]
    )

    assert read_splines(io.BytesIO(data)) == {5: first, 9: second}


@pytest.mark.parametrize("data", [b"\x01\x00", bytes([2, 0, 0, 0, 0, 0, 0, 0])])
def test_other_files_are_rejected(data):
    with pytest.raises(ShapesError):
        read_splines(io.BytesIO(data))


def test_a_cut_file_is_rejected():
    data = shapes_file([(2, spline_data("lane", 5, [(1.0, 2.0, 3.0)]))])

    with pytest.raises(ShapesError):
        read_splines(io.BytesIO(data[:-8]))
