import math

import pytest

from autodrive_editor.editing.path_shapes import (
    PathShape,
    arc_polyline,
    bezier_polyline,
    default_handles,
    shape_polyline,
    spaced_points,
)


@pytest.mark.parametrize(("spacing", "segments"), [(3, 3), (2.4, 4)])
def test_spacing_divides_the_length_evenly(spacing, segments):
    points = spaced_points([(0, 0), (10, 0)], spacing)

    assert len(points) == segments + 1
    assert [math.dist(a, b) for a, b in zip(points, points[1:], strict=False)] == pytest.approx(
        [10 / segments] * segments
    )


def test_ends_are_kept_and_short_paths_have_one_segment():
    assert spaced_points([(0, 0), (1, 0)], 5) == [(0, 0), (1, 0)]


def test_spacing_follows_a_bent_polyline():
    points = spaced_points([(0, 0), (4, 0), (4, 4)], 2)

    assert points == pytest.approx([(0, 0), (2, 0), (4, 0), (4, 2), (4, 4)])


@pytest.mark.parametrize("spacing", [0, -1])
def test_spacing_must_be_positive(spacing):
    with pytest.raises(ValueError):
        spaced_points([(0, 0), (10, 0)], spacing)


@pytest.mark.parametrize("through", [(5, 3), (5, -3)])
def test_arc_lies_on_the_circle_through_the_three_points(through):
    start, end = (0, 0), (10, 0)
    points = arc_polyline(start, through, end)

    center_z = (through[1] ** 2 - 25) / (2 * through[1])
    center = (5, center_z)
    radius = math.dist(start, center)

    assert points[0] == start and points[-1] == end
    assert all(math.dist(p, center) == pytest.approx(radius) for p in points)
    assert min(math.dist(p, through) for p in points) < 0.05


def test_arc_bulges_to_the_side_of_the_through_point():
    above = arc_polyline((0, 0), (5, 3), (10, 0))
    below = arc_polyline((0, 0), (5, -3), (10, 0))

    assert all(z >= -1e-9 for _, z in above)
    assert all(z <= 1e-9 for _, z in below)


def test_arc_can_be_longer_than_a_half_circle():
    points = arc_polyline((0, 0), (5, 20), (10, 0))

    assert max(z for _, z in points) == pytest.approx(20, abs=0.05)
    assert max(x for x, _ in points) > 10


def test_collinear_arc_is_a_straight_line():
    assert arc_polyline((0, 0), (5, 0), (10, 0)) == [(0, 0), (10, 0)]


def test_bezier_with_default_handles_is_straight():
    start, end = (0, 0), (9, 6)
    handles = default_handles(PathShape.BEZIER, start, end)
    points = bezier_polyline(start, *handles, end)

    assert points[0] == start and points[-1] == pytest.approx(end)
    assert all(abs(6 * x - 9 * z) < 1e-6 for x, z in points)


def test_quadratic_bezier_peaks_halfway_to_its_control_point():
    points = bezier_polyline((0, 0), (5, 10), (10, 0))

    assert points[0] == (0, 0) and points[-1] == pytest.approx((10, 0))
    assert max(z for _, z in points) == pytest.approx(5)


def test_quadratic_bezier_default_handle_is_in_the_middle():
    assert default_handles(PathShape.BEZIER, (0, 0), (10, 4), control_points=1) == [(5, 2)]


def test_default_arc_handle_is_beside_the_middle():
    (handle,) = default_handles(PathShape.ARC, (0, 0), (10, 0))

    assert handle[0] == pytest.approx(5)
    assert handle[1] != 0


def test_line_polyline_is_start_and_end():
    assert shape_polyline(PathShape.LINE, (0, 0), (3, 4), []) == [(0, 0), (3, 4)]
