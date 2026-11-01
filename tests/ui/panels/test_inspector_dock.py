from autodrive_editor.ui.panels.inspector_dock import InspectorDock


def test_shows_the_text_or_nothing_selected(qapp):
    dock = InspectorDock()

    assert dock.node_info_value.text() == "Nothing selected"

    dock.set_node_info("Node 3")
    assert dock.node_info_value.text() == "Node 3"

    dock.set_node_info(None)
    assert dock.node_info_value.text() == "Nothing selected"


def test_inspector_follows_the_selection(zoomed_window):
    window = zoomed_window
    inspector = window.inspector_dock

    window.node_selection.replace({2}, primary_node_id=2)
    assert inspector.node_info_value.text().startswith("Node 2")

    window.node_selection.clear()
    assert inspector.node_info_value.text() == "Nothing selected"


def test_inspector_is_tabbed_with_markers_and_on_top(window, qapp):
    window.show()
    qapp.processEvents()

    assert window.tabifiedDockWidgets(window.inspector_dock) == [window.marker_dock]
    assert not window.inspector_dock.visibleRegion().isEmpty()


def test_debug_info_opens_from_help_and_keeps_only_runtime_numbers(window):
    help_menu = next(a.menu() for a in window.menuBar().actions() if a.text() == "Help")
    view_menu = next(a.menu() for a in window.menuBar().actions() if a.text() == "View")
    toggle = window.debug_dock.toggleViewAction()

    assert toggle in help_menu.actions()
    assert toggle not in view_menu.actions()
    assert window.inspector_dock.toggleViewAction() in view_menu.actions()
    assert not hasattr(window.debug_dock, "node_info_value")
