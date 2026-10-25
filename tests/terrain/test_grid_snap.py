import math

import pytest

from autodrive_editor.terrain.background_map import snap_to_grid


def close(point, expected):
    return all(math.isclose(a, b, abs_tol=1e-9) for a, b in zip(point, expected, strict=True))


def test_snaps_to_nearest_grid_point():
    assert close(snap_to_grid(13.0, -6.0, 10.0, 0.0), (10.0, -10.0))
    assert close(snap_to_grid(16.0, 4.9, 10.0, 0.0), (20.0, 0.0))


def test_other_spacing():
    assert close(snap_to_grid(3.7, 1.2, 2.5, 0.0), (2.5, 0.0))


@pytest.mark.parametrize("angle", [30.0, 45.0, 315.0])
def test_rotated_grid_points_stay_on_the_rotated_grid(angle):
    radians = math.radians(angle)
    # Grid point (2, 1) of a 10 m grid rotated by angle, plus a small offset.
    grid_x, grid_z = 20.0, 10.0
    x = grid_x * math.cos(radians) - grid_z * math.sin(radians)
    z = grid_x * math.sin(radians) + grid_z * math.cos(radians)

    assert close(snap_to_grid(x + 2.0, z - 1.5, 10.0, angle), (x, z))
