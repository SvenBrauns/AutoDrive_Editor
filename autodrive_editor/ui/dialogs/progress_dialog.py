"""The progress dialog shared by the generators: the work runs on a background thread, the
dialog appears when it takes longer than half a second, and Cancel throws the whole run away."""

from collections.abc import Callable

from PySide6.QtCore import QEventLoop, QObject, Qt, Signal
from PySide6.QtWidgets import QProgressDialog

from autodrive_editor.editing.operations.background_search import BackgroundSearch
from autodrive_editor.i18n import tr

# Milliseconds before the dialog appears.
SHOW_AFTER = 500

# report(done, total, text) and cancelled() as the work gets them.
Report = Callable[[int, int, str], None]
Cancelled = Callable[[], bool]


class GeneratorFailed(Exception):
    """The work raised an exception; it is in the log file."""


class _Bridge(QObject):
    # From the work's thread to the dialog: done, total, text.
    progress = Signal(int, int, str)


def run_with_progress(title: str, work: Callable[[Report, Cancelled], object], parent=None):
    """Runs work(report, cancelled) and returns its result, or None after Cancel. The work
    should check cancelled() now and then and stop; its result is then thrown away. Raises
    GeneratorFailed when the work failed."""

    dialog = QProgressDialog(title, tr("Cancel"), 0, 0, parent)
    dialog.setWindowTitle(title)
    dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
    dialog.setMinimumDuration(SHOW_AFTER)
    dialog.setAutoReset(False)
    dialog.setAutoClose(False)
    # Starts the timer that shows the dialog after SHOW_AFTER.
    dialog.setValue(0)

    def show_progress(done: int, total: int, text: str):
        if not dialog.wasCanceled():
            dialog.setMaximum(total)
            dialog.setValue(done)
            dialog.setLabelText(text)

    bridge = _Bridge(dialog)
    bridge.progress.connect(show_progress)
    loop = QEventLoop()
    outcome = {}

    def finish(**values):
        outcome.update(values)
        loop.quit()

    search = BackgroundSearch(dialog)
    cancelled = search.start(
        lambda is_cancelled: work(bridge.progress.emit, is_cancelled),
        lambda result: finish(result=result),
        lambda: finish(failed=True),
    )
    dialog.canceled.connect(cancelled.set)

    # Until the work has ended, also after Cancel, so it never reports to a closed dialog.
    loop.exec()
    # Closing the dialog emits canceled too.
    was_cancelled = cancelled.is_set()
    dialog.close()
    dialog.deleteLater()

    if was_cancelled:
        return None

    if outcome.get("failed"):
        raise GeneratorFailed

    return outcome["result"]
