"""Sizes on screen for things whose size is given in metres on the map."""

import math

from PySide6.QtGui import QPainter


def view_scale(painter: QPainter) -> float:
    """Screen pixels per metre for the painter's current transform (zoom, rotation ignored)."""

    transform = painter.worldTransform()

    return math.hypot(transform.m11(), transform.m12())


def screen_size(map_size: float, scale: float, minimum_px: float, maximum_px: float) -> float:
    """The map size in pixels at this scale, kept between minimum_px and maximum_px."""

    return min(max(map_size * scale, minimum_px), maximum_px)


def fade_in(value: float, start: float, end: float) -> float:
    """0 up to start, 1 from end on, smooth in between."""

    if end <= start:
        return 1.0 if value >= end else 0.0

    t = min(max((value - start) / (end - start), 0.0), 1.0)

    return t * t * (3 - 2 * t)
