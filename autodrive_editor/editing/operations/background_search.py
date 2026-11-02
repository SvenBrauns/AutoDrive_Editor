"""Searches on a background thread whose result or failure comes back on the UI thread."""

import logging
import threading
from collections.abc import Callable

from PySide6.QtCore import QObject, Signal

logger = logging.getLogger(__name__)


class BackgroundSearch(QObject):
    # From the search thread: the handler to call on the UI thread and its argument.
    _done = Signal(object, object)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._done.connect(lambda handler, value: handler(value))
        self._running: list[tuple[threading.Thread, threading.Event]] = []

    def start(
        self,
        search: Callable[[Callable[[], bool]], object],
        on_done: Callable[[object], None],
        on_failed: Callable[[], None],
    ) -> threading.Event:
        """Runs search(cancelled) on a new thread. The search must only use inputs read on the UI
        thread before. on_done gets its result; after an exception, which is logged, on_failed is
        called. Returns the event that cancels the search."""

        cancelled = threading.Event()

        def run():
            try:
                result = search(cancelled.is_set)
            except Exception:
                logger.exception("Background search failed")
                self._emit(lambda _: on_failed(), None)
            else:
                self._emit(on_done, result)

        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        self._running = [(t, c) for t, c in self._running if t.is_alive()]
        self._running.append((thread, cancelled))

        return cancelled

    def stop(self):
        """Cancels all running searches and waits until they have ended, so none reports to a
        window that is deleted meanwhile."""

        for _, cancelled in self._running:
            cancelled.set()

        for thread, _ in self._running:
            thread.join()

        self._running = []

    def _emit(self, handler, value):
        try:
            self._done.emit(handler, value)
        except RuntimeError:
            # The window was closed during the search.
            pass
