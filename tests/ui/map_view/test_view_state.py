"""Reading and restoring where the map view looks."""

import pytest

from autodrive_editor.settings.view_state import ViewState


def test_view_state_is_restored(loaded_window, qapp):
    view = loaded_window.view
    view.setSceneRect(-1000, -1000, 2000, 2000)
    # Scroll bars appear for the larger scene before the view is set.
    qapp.processEvents()
    state = ViewState(15.0, -5.0, 3.0, 30.0)

    view.show_view_state(state)
    qapp.processEvents()
    restored = view.view_state()

    assert restored.zoom == pytest.approx(3.0)
    assert restored.rotation == pytest.approx(30.0)
    assert (restored.x, restored.z) == (pytest.approx(15.0, abs=1), pytest.approx(-5.0, abs=1))
