import pytest
from PySide6.QtGui import QImage, QPainter, QTransform

from autodrive_editor.rendering.screen_size import fade_in, screen_size, view_scale


@pytest.mark.parametrize(
    ("scale", "expected"),
    [(0.01, 1.0), (4.0, 2.0), (100.0, 3.0)],
)
def test_screen_size_follows_the_zoom_within_its_limits(scale, expected):
    assert screen_size(0.5, scale, 1.0, 3.0) == expected


def test_fade_in_is_smooth_between_its_limits():
    values = [fade_in(value, 2.0, 4.0) for value in (1.0, 2.0, 2.5, 3.0, 3.5, 4.0, 9.0)]

    assert values[:2] == [0.0, 0.0]
    assert values[-2:] == [1.0, 1.0]
    assert values[3] == pytest.approx(0.5)
    assert values == sorted(values)


def test_fade_in_without_range_switches_at_the_end():
    assert fade_in(1.9, 2.0, 2.0) == 0.0
    assert fade_in(2.0, 2.0, 2.0) == 1.0


def test_view_scale_ignores_rotation(qapp):
    image = QImage(10, 10, QImage.Format_ARGB32)
    painter = QPainter(image)
    painter.setTransform(QTransform().rotate(30).scale(2.5, 2.5))

    assert view_scale(painter) == pytest.approx(2.5)

    painter.end()
