from PySide6.QtGui import QAction

from autodrive_editor.editing.junctions.junction import Stem
from autodrive_editor.editing.junctions.junction_box import Style
from autodrive_editor.editing.operations.road_network import RoadMode, RoadSettings
from autodrive_editor.ui.panels.generate_options import GenerateOptionsWidget
from autodrive_editor.ui.tools.generate_tool import GenerateTask


def task_actions():
    return {task: QAction(task.display_name) for task in GenerateTask}


def test_each_task_has_a_button_for_its_action(qapp):
    actions = task_actions()
    widget = GenerateOptionsWidget(actions, GenerateTask.ROUTE, Stem.AUTO, 5.5)

    assert {t: b.defaultAction() for t, b in widget.task_buttons.items()} == actions


def test_only_the_options_of_the_chosen_task_are_shown(qapp):
    widget = GenerateOptionsWidget(task_actions(), GenerateTask.ROUTE, Stem.AUTO, 5.5)

    assert widget.junction_options.isHidden()

    widget.set_task(GenerateTask.JUNCTION)

    assert not widget.junction_options.isHidden()
    assert widget.route_options.isHidden()


def test_changing_the_stem_or_gap_reports_both(qapp):
    widget = GenerateOptionsWidget(task_actions(), GenerateTask.JUNCTION, Stem.AUTO, 5.5)
    changes = []
    widget.stem_changed.connect(lambda stem, gap: changes.append((stem, gap)))

    widget.stem_box.setCurrentIndex(widget.stem_box.findData(Stem.TWO_LANES))
    widget.gap_box.setValue(7.0)

    assert changes == [(Stem.TWO_LANES, 5.5), (Stem.TWO_LANES, 7.0)]


def test_the_style_starts_as_given_and_reports_changes(qapp):
    widget = GenerateOptionsWidget(task_actions(), GenerateTask.JUNCTION, Stem.AUTO, 5.5, Style.BOX)
    changes = []
    widget.style_changed.connect(changes.append)

    assert widget.style_box.currentData() == Style.BOX

    widget.style_box.setCurrentIndex(widget.style_box.findData(Style.CURVES))

    assert changes == [Style.CURVES]


def test_road_options_report_the_settings_and_create_only_for_the_whole_map(qapp):
    widget = GenerateOptionsWidget(task_actions(), GenerateTask.ROADS, Stem.AUTO, 5.5)
    changes, creates = [], []
    widget.road_settings_changed.connect(changes.append)
    widget.create_roads_requested.connect(lambda: creates.append(True))

    assert not widget.road_options.isHidden()
    widget.create_roads_button.click()
    widget.road_existing_box.setCurrentIndex(widget.road_existing_box.findData(True))
    widget.road_mode_box.setCurrentIndex(widget.road_mode_box.findData(RoadMode.BOX))

    assert creates == [True]
    assert changes[-1] == RoadSettings(RoadMode.BOX, replace=True)
    assert not widget.create_roads_button.isEnabled()
