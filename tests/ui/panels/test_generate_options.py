from autodrive_editor.editing.junction import Stem
from autodrive_editor.ui.panels.generate_options import GenerateOptionsWidget
from autodrive_editor.ui.tools.generate_tool import GenerateTask


def test_stem_options_are_shown_for_the_junction_task_only(qapp):
    widget = GenerateOptionsWidget(GenerateTask.ROUTE, Stem.AUTO, 5.5)

    assert widget.junction_options.isHidden()

    widget.task_buttons[GenerateTask.JUNCTION].setChecked(True)

    assert not widget.junction_options.isHidden()


def test_changing_the_stem_or_gap_reports_both(qapp):
    widget = GenerateOptionsWidget(GenerateTask.JUNCTION, Stem.AUTO, 5.5)
    changes = []
    widget.stem_changed.connect(lambda stem, gap: changes.append((stem, gap)))

    widget.stem_box.setCurrentIndex(widget.stem_box.findData(Stem.TWO_LANES))
    widget.gap_box.setValue(7.0)

    assert changes == [(Stem.TWO_LANES, 5.5), (Stem.TWO_LANES, 7.0)]
