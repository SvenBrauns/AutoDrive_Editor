"""Marking game picture tiles for a refresh."""

import pytest
from mouse_helpers import click, drag, hover, press_escape, view_pos
from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QApplication

from autodrive_editor.rendering.items.picture_grid_item import PictureGridItem
from autodrive_editor.terrain import game_picture
from autodrive_editor.terrain.game_picture import GamePicture, PictureGrid
from autodrive_editor.ui.tools.picture_refresh_tool import PictureRefreshTool


@pytest.fixture
def tool(zoomed_window, tmp_path, monkeypatch):
    """A 40 m map in 4 × 4 tiles of 10 m; the view shows x 0…20 around z 0."""

    monkeypatch.setattr(game_picture, "TILE_PX", 20)
    picture = GamePicture.create(tmp_path / "1", PictureGrid(40, 0.5))
    tool = PictureRefreshTool(zoomed_window.view, picture, 500, None, None, None)
    tool.sent, tool.closed, tool.statuses = [], [], []
    tool.send, tool.close = tool.sent.append, lambda: tool.closed.append(True)
    tool.show_status = tool.statuses.append
    tool.window = zoomed_window
    zoomed_window.view.set_overlay_tool(tool)
    return tool


def at(tool, x, z):
    return view_pos(tool.window, x, z)


def press_enter(window):
    QApplication.sendEvent(window.view, QKeyEvent(QEvent.KeyPress, Qt.Key_Return, Qt.NoModifier))


def test_the_grid_shows_while_the_tool_is_on(tool):
    assert tool.item.scene() is tool.window.scene

    tool.window.view.set_overlay_tool(None)

    assert not any(isinstance(item, PictureGridItem) for item in tool.window.scene.items())


def test_click_toggles_a_tile(tool):
    click(tool.window, at(tool, 5, -5))

    assert tool.marked == {(2, 1)}
    assert tool.item.marked == {(2, 1)}

    click(tool.window, at(tool, 5, -5))

    assert tool.marked == set()


def test_left_drag_pans_without_marking(tool):
    drag(tool.window, at(tool, 5, -5), at(tool, 15, -5))

    assert tool.marked == set()


def test_right_drag_marks_the_touched_tiles_and_ctrl_unmarks(tool):
    drag(tool.window, at(tool, 1, -9), at(tool, 12, -1), Qt.RightButton)

    assert tool.marked == {(2, 1), (3, 1)}

    drag(
        tool.window,
        at(tool, 12, -6),
        at(tool, 14, -4),
        Qt.RightButton,
        modifiers=Qt.ControlModifier,
    )

    assert tool.marked == {(2, 1)}


def test_box_in_a_rotated_view(tool):
    tool.window.view.set_exact_rotation_angle(45)
    QApplication.processEvents()

    # On the map the box is a diamond around (8.5, -1.5): its bounding box reaches tile 3, 2,
    # the diamond does not.
    drag(tool.window, at(tool, 8.5, -3.5), at(tool, 8.5, 0.5), Qt.RightButton)

    assert tool.marked == {(2, 1), (3, 1), (2, 2)}


def test_escape_clears_the_marks_then_ends_the_tool(tool):
    click(tool.window, at(tool, 5, -5))

    press_escape(tool.window)
    assert tool.marked == set() and not tool.closed

    press_escape(tool.window)
    assert tool.closed


def test_enter_sends_the_marked_tiles_row_by_row(tool):
    press_enter(tool.window)
    assert tool.sent == []

    click(tool.window, at(tool, 15, -5))
    click(tool.window, at(tool, 5, 5))
    click(tool.window, at(tool, 5, -5))
    press_enter(tool.window)

    assert tool.sent == [[(2, 1), (3, 1), (2, 2)]]


def test_status_shows_the_hovered_tile_and_the_marks(tool):
    tool.picture.record_tile(2, 1, "2026-11-01T14:20:05")

    hover(tool.window, at(tool, 5, 5))
    assert tool.statuses[-1].startswith("Tile 2, 2 · not captured – Click a tile")

    hover(tool.window, at(tool, 5, -5))
    assert tool.statuses[-1].startswith("Tile 2, 1 · captured 2026-11-01 14:20 – ")

    click(tool.window, at(tool, 5, -5))
    assert tool.statuses[-1].endswith("1 tiles marked · about 1 min · Enter refreshes, Esc clears")
