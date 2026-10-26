from autodrive_editor.rendering.display_style import DisplayStyle
from autodrive_editor.ui.panels.display_options_dialog import DisplayOptionsDialog


def test_dialog_shows_and_applies_every_size(qapp):
    dialog = DisplayOptionsDialog(DisplayStyle(node_max_px=30.0))
    applied = []
    dialog.style_applied.connect(applied.append)

    assert dialog.size_inputs["node_max_px"].value() == 30.0

    dialog.size_inputs["connection_max_px"].setValue(5.0)
    dialog.color_buttons["dual_connection_color"].set_color((1, 2, 3))
    dialog._apply_changes()

    assert applied == [
        DisplayStyle(node_max_px=30.0, connection_max_px=5.0, dual_connection_color=(1, 2, 3))
    ]


def test_defaults_button_loads_the_default_style(qapp):
    dialog = DisplayOptionsDialog(DisplayStyle(node_diameter=5.0))

    dialog.default_button.click()

    assert dialog._build_style() == DisplayStyle()
