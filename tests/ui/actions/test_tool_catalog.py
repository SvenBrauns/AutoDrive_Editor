from PySide6.QtGui import QColor, QIcon

from autodrive_editor.ui.actions.tool_catalog import (
    DRAW_TOOL,
    HISTORY_ICON_DISABLED_COLOR,
    HISTORY_ICON_DISABLED_DARK_COLOR,
    history_icon,
    merged_tool_of,
    variant_text,
)
from autodrive_editor.ui.tools.interaction_mode import InteractionMode


def disabled_colors(icon: QIcon) -> set[str]:
    image = icon.pixmap(32, QIcon.Mode.Disabled).toImage()

    return {
        QColor(image.pixel(x, y)).name()
        for x in range(image.width())
        for y in range(image.height())
        if image.pixelColor(x, y).alpha() == 255
    }


def test_disabled_history_icon_matches_the_theme(qapp):
    assert disabled_colors(history_icon("undo")) == {HISTORY_ICON_DISABLED_COLOR}
    assert disabled_colors(history_icon("undo", dark=True)) == {HISTORY_ICON_DISABLED_DARK_COLOR}


def test_merged_tool_of_finds_the_tool_of_a_variant():
    assert merged_tool_of(InteractionMode.DRAW_ARC) is DRAW_TOOL
    assert merged_tool_of(InteractionMode.MOVE_NODES) is None


def test_variant_text_names_tool_and_variant():
    assert variant_text(DRAW_TOOL, DRAW_TOOL.variants[2]) == "Draw – Bézier"
    assert DRAW_TOOL.modes == (
        InteractionMode.DRAW_LINE,
        InteractionMode.DRAW_ARC,
        InteractionMode.DRAW_BEZIER,
        InteractionMode.DRAW_PARALLEL,
    )
