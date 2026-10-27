"""Light or dark look of the editor."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

# "system" maps to Unknown, which lets Qt follow the Windows setting again.
COLOR_SCHEMES = {
    "system": Qt.ColorScheme.Unknown,
    "light": Qt.ColorScheme.Light,
    "dark": Qt.ColorScheme.Dark,
}


def apply_theme(app: QApplication, theme: str):
    app.styleHints().setColorScheme(COLOR_SCHEMES[theme])
