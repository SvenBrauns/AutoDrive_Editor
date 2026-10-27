import logging
import sys

import pytest

from autodrive_editor.error_log import LOG_FILE_NAME, install_error_handler, logger, setup_logging


@pytest.fixture
def log_file(tmp_path):
    root = logging.getLogger()
    handlers, level = list(root.handlers), root.level

    path = setup_logging(tmp_path / "logs")

    yield path

    for handler in root.handlers[len(handlers) :]:
        handler.close()
        root.removeHandler(handler)

    root.setLevel(level)


def test_log_messages_go_to_the_log_file(log_file):
    logger.info("Editor started")

    assert log_file.name == LOG_FILE_NAME
    assert "INFO autodrive_editor: Editor started" in log_file.read_text(encoding="utf-8")


def test_unexpected_error_is_logged_and_shown(log_file, monkeypatch):
    shown = []
    monkeypatch.setattr(sys, "excepthook", sys.excepthook)
    install_error_handler(shown.append)

    try:
        raise ValueError("broken node")
    except ValueError:
        sys.excepthook(*sys.exc_info())

    assert "ValueError: broken node" in shown[0]
    assert "Traceback" in shown[0]
    assert "ValueError: broken node" in log_file.read_text(encoding="utf-8")
