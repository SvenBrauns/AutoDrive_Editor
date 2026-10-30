"""Junction task of the Generate tool with the real window."""

import pytest
from mouse_helpers import click, drag, press_escape, view_pos
from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QApplication

from autodrive_editor.editing.junction import Stem
from autodrive_editor.editing.junction_box import Style
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


def press_enter(window):
    QApplication.sendEvent(window.view, QKeyEvent(QEvent.KeyPress, Qt.Key_Return, Qt.NoModifier))


def test_release_shows_the_tip_handle_and_enter_adds_the_junction(window):
    data = window.project_coordinator.autodrive_data
    start, end = view_pos(window, 5, 0), view_pos(window, 5, 15)

    drag(window, start, end, release=False)

    tool = window.generate_tool.current
    assert tool._item.isVisible() and not tool._item.path().isEmpty()
    assert not tool._handle.isVisible()

    drag(window, end, end)

    assert len(data.nodes) == 13
    assert tool._handle.isVisible()
    handle = tool._handle.pos()
    assert (handle.x(), handle.y()) == pytest.approx((5, 15), abs=0.5)

    press_enter(window)

    assert len(data.nodes) > 13
    assert window.edit_history.is_planning and window.edit_history.has_plan_edits
    assert not tool._item.isVisible() and not tool._handle.isVisible()


def test_dragging_the_tip_bends_the_stem_and_a_click_away_adds_it(window):
    data = window.project_coordinator.autodrive_data
    drag(window, view_pos(window, 5, 0), view_pos(window, 5, 15))

    drag(window, view_pos(window, 5, 15), view_pos(window, 12, 20))

    stem = window.junction_operation.preview.stem
    assert stem[-1][:2] == pytest.approx((12, 20), abs=0.5)
    assert len(data.nodes) == 13

    click(window, view_pos(window, -10, 20))

    assert len(data.nodes) > 13


def test_dropping_the_tip_on_a_node_joins_it(window):
    drag(window, view_pos(window, 5, 0), view_pos(window, 5, 15))

    drag(window, view_pos(window, 5, 15), view_pos(window, 20.3, 0.2))

    assert window.junction_operation.preview.tip_id == 9


def test_escape_cancels_the_bending(window):
    data = window.project_coordinator.autodrive_data
    drag(window, view_pos(window, 5, 0), view_pos(window, 5, 15))

    press_escape(window)

    assert window.junction_operation.preview is None
    assert not window.junction_operation.is_bending
    assert len(data.nodes) == 13


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
        following = [i for i in range(start + 1, len(elements)) if elements[i].isMoveTo()]
        end = elements[(following[0] if following else len(elements)) - 1]
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
    options.style_box.setCurrentIndex(options.style_box.findData(Style.CURVES))
    assert window.settings.junction_style == Style.CURVES


def test_undo_in_step_two_cancels_the_junction_not_the_last_edit(window):
    data = window.project_coordinator.autodrive_data
    drag(window, view_pos(window, 5, 0), view_pos(window, 5, 15))
    press_enter(window)
    added = len(data.nodes)
    drag(window, view_pos(window, -35, 0), view_pos(window, -35, 15))

    window.actions.undo_action.trigger()

    assert window.junction_operation.preview is None
    assert len(data.nodes) == added
    window.actions.undo_action.trigger()
    assert len(data.nodes) == 13
