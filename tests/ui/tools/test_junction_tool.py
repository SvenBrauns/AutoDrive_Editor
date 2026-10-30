"""Junction task of the Generate tool with the real window."""

import pytest
from mouse_helpers import drag, press_escape, view_pos

from autodrive_editor.editing.junction import Stem
from autodrive_editor.ui.tools.generate_tool import GenerateTask


@pytest.fixture
def window(window, write_xml, qapp):
    """An east-bound road at z = 0 from x = -60 to 60, nodes 10 m apart (IDs 1–13)."""

    ids = range(1, 14)
    path = write_xml(
        x=";".join(str(x) for x in range(-60, 61, 10)),
        z=";".join("0" for _ in ids),
        y=";".join("0" for _ in ids),
        flags=";".join("0" for _ in ids),
        out=";".join(str(i + 1) if i < 13 else "" for i in ids),
        incoming=";".join(str(i - 1) if i > 1 else "" for i in ids),
    )
    window.project_coordinator.load_xml_file(path)
    window.view.set_zoom_level(4.0)
    window.view.centerOn(5, 10)
    window.find_route_operation.costmap_provider = lambda: None
    window.set_generate_task(GenerateTask.JUNCTION)
    qapp.processEvents()

    return window


def test_dragging_from_a_road_previews_and_release_adds_the_junction(window):
    data = window.project_coordinator.autodrive_data
    start, end = view_pos(window, 5, 0), view_pos(window, 5, 15)

    drag(window, start, end, release=False)

    tool = window.generate_tool.current
    assert tool._item.isVisible() and not tool._item.path().isEmpty()

    drag(window, end, end)

    assert len(data.nodes) > 13
    assert window.edit_history.is_planning and window.edit_history.has_plan_edits
    assert not tool._item.isVisible()


def test_escape_cancels_the_preview(window):
    data = window.project_coordinator.autodrive_data
    drag(window, view_pos(window, 5, 0), view_pos(window, 5, 15), release=False)

    press_escape(window)

    assert window.junction_operation.preview is None
    assert len(data.nodes) == 13


def test_dragging_beside_the_road_pans(window):
    data = window.project_coordinator.autodrive_data

    drag(window, view_pos(window, 5, 20), view_pos(window, 5, 30))

    assert window.junction_operation.preview is None
    assert len(data.nodes) == 13


def test_the_preview_shows_both_lanes_of_a_two_lane_stem(window):
    window.junction_operation.stem_provider = lambda: (Stem.TWO_LANES, 6.0)

    drag(window, view_pos(window, 5, 0), view_pos(window, 5, 25), release=False)

    path = window.generate_tool.current._item.path()
    elements = [path.elementAt(i) for i in range(path.elementCount())]
    # A stem line from 3 m to each side of the stem's centre line towards the drag end, drawn
    # after the curves.
    x, z, _ = window.junction_operation.preview.junction
    for lane_x in (x - 3, x + 3):
        start = max(
            i
            for i, element in enumerate(elements)
            if element.isMoveTo() and (element.x, element.y) == pytest.approx((lane_x, z))
        )
        end = elements[start + 1]
        assert (end.x, end.y) == pytest.approx((lane_x, 25), abs=0.5)


def test_the_stem_options_fit_into_the_menu_and_are_saved(window, qapp):
    options = window.generate_options
    menu = window.actions.quick_access_toolbar.widgetForAction(
        window.actions.generate_action
    ).menu()

    def opened_height():
        menu.popup(menu.pos())
        qapp.processEvents()
        height = menu.height()
        menu.close()
        return height

    route_height = opened_height()
    options.task_buttons[GenerateTask.JUNCTION].setChecked(True)
    options.gap_box.setValue(7.0)
    qapp.processEvents()

    assert opened_height() > route_height
    assert window.settings.junction_stem == (Stem.AUTO, 7.0)
