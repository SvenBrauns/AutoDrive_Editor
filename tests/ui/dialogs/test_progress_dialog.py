import time

import pytest
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QProgressDialog, QPushButton

from autodrive_editor.ui.dialogs.progress_dialog import GeneratorFailed, run_with_progress


def test_the_result_of_the_work_is_returned(qapp):
    def work(report, cancelled):
        for done in range(3):
            report(done, 3, f"Stop {done + 1} of 3")
        return 42

    assert run_with_progress("Stations", work) == 42


def test_the_dialog_appears_after_a_while_and_cancel_throws_the_run_away(qapp):
    def cancel():
        widgets = QApplication.topLevelWidgets()
        (dialog,) = [w for w in widgets if isinstance(w, QProgressDialog) and w.isVisible()]
        dialog.findChild(QPushButton).click()

    def work(report, cancelled):
        deadline = time.monotonic() + 5
        while not cancelled() and time.monotonic() < deadline:
            time.sleep(0.01)
        return "half built"

    QTimer.singleShot(700, cancel)

    assert run_with_progress("Stations", work) is None


def test_a_failed_work_raises(qapp):
    def work(report, cancelled):
        raise ValueError("broken")

    with pytest.raises(GeneratorFailed):
        run_with_progress("Stations", work)
