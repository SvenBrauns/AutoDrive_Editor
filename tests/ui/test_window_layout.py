from autodrive_editor.ui.main_window import MainWindow


def test_window_size_and_panels_are_restored_at_the_next_start(window, qapp):
    window.resize(1000, 700)
    window.check_dock.show()
    window.marker_dock.hide()
    qapp.processEvents()
    size = window.size()
    window.close()

    next_window = MainWindow()
    next_window.show()
    qapp.processEvents()

    try:
        assert next_window.size() == size
        assert size.height() == 700
        assert next_window.check_dock.isVisible()
        assert not next_window.marker_dock.isVisible()
    finally:
        next_window.close()
        next_window.deleteLater()
