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

        threading.Thread(target=run, daemon=True).start()

        return cancelled

    def _emit(self, handler, value):
        try:
            self._done.emit(handler, value)
        except RuntimeError:
            # The window was closed during the search.
            pass
