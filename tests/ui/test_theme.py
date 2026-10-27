from types import SimpleNamespace

from PySide6.QtCore import Qt

from autodrive_editor.ui.theme import apply_theme


def test_theme_sets_the_color_scheme():
    # The offscreen test platform ignores color schemes, so the call is recorded instead.
    schemes = []
    app = SimpleNamespace(styleHints=lambda: SimpleNamespace(setColorScheme=schemes.append))

    for theme in ("dark", "light", "system"):
        apply_theme(app, theme)

    assert schemes == [Qt.ColorScheme.Dark, Qt.ColorScheme.Light, Qt.ColorScheme.Unknown]
