"""The log file and the handling of unexpected errors."""

import logging
import sys
import traceback
from collections.abc import Callable
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_FILE_NAME = "editor.log"
MAX_LOG_BYTES = 1_000_000
OLD_LOG_FILES = 3

logger = logging.getLogger("autodrive_editor")


def setup_logging(log_directory: Path) -> Path:
    """Writes log messages to editor.log in the folder. The file is kept to
    about 1 MB; older contents move to editor.log.1 to .3."""

    log_directory.mkdir(parents=True, exist_ok=True)
    log_path = log_directory / LOG_FILE_NAME

    handler = RotatingFileHandler(
        log_path, maxBytes=MAX_LOG_BYTES, backupCount=OLD_LOG_FILES, encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))

    root = logging.getLogger()
    root.addHandler(handler)
    root.setLevel(logging.INFO)

    return log_path


def install_error_handler(show_error: Callable[[str], None]):
    """Logs every unhandled exception, also those raised in Qt slots, and
    passes its traceback to show_error. The editor keeps running."""

    def handle(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        details = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))

        logger.error("Unexpected error\n%s", details)

        show_error(details)

    sys.excepthook = handle
