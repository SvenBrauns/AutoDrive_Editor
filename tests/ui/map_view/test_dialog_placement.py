"""Dialogs beside the map open away from the map points they are about."""

import pytest
from PySide6.QtCore import QPoint, QPointF
from PySide6.QtWidgets import QDialog

from autodrive_editor.ui.map_view.dialog_placement import place_beside


def global_x(view, x, z) -> int:
    return view.viewport().mapToGlobal(view.mapFromScene(QPointF(x, z))).x()


@pytest.mark.parametrize("width_share", [0.3, 0.6])
def test_the_dialog_leaves_the_points_free(zoomed_window, qapp, width_share):
    view = zoomed_window.view
    # A map large enough to pan.
    view.setSceneRect(-1000, -1000, 2000, 2000)
    view.centerOn(10, 0)
    dialog = QDialog(zoomed_window)
    dialog.resize(int(view.viewport().width() * width_share), 100)
    # Just right of the middle of the map.
    points = [(12.0, 0.0), (14.0, 5.0)]

    place_beside(dialog, view, points)

    left = dialog.pos().x()
    assert left < view.viewport().mapToGlobal(QPoint(0, 0)).x() + 50, "on the left"
    for x, z in points:
        assert not left <= global_x(view, x, z) <= left + dialog.width()
