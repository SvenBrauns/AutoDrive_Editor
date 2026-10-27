from PySide6.QtGui import QColor, QIcon

from autodrive_editor.ui.actions.tool_catalog import (
    HISTORY_ICON_DISABLED_COLOR,
    HISTORY_ICON_DISABLED_DARK_COLOR,
    history_icon,
)


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
