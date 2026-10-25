import os
import sys
import traceback

# Must be set before PySide6 creates an application, so no window opens.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture(autouse=True)
def fail_on_slot_exceptions():
    """Qt only prints exceptions raised inside slots. Fail the test instead."""
    caught = []
    previous_hook = sys.excepthook
    sys.excepthook = lambda *exc_info: caught.append(exc_info)

    yield

    sys.excepthook = previous_hook

    if caught:
        details = "".join(
            "".join(traceback.format_exception(*exc_info))
            for exc_info in caught
        )
        pytest.fail(f"Unhandled exception in a Qt slot:\n{details}", pytrace=False)


@pytest.fixture
def write_xml(tmp_path):
    """Write an AutoDrive XML file and return its path."""

    def _write(
        x="0;10;20",
        y="0;0;0",
        z="0;0;0",
        out="2;3;",
        incoming=";1;2",
        flags="0;0;0",
        markers="",
        raw=None
    ):
        if raw is None:
            optional = ""

            if out is not None:
                optional += f"<out>{out}</out>"

            if incoming is not None:
                optional += f"<in>{incoming}</in>"

            if flags is not None:
                optional += f"<flags>{flags}</flags>"

            raw = (
                "<AutoDrive>"
                "<waypoints>"
                f"<x>{x}</x><y>{y}</y><z>{z}</z>"
                f"{optional}"
                "</waypoints>"
                f"<markers>{markers}</markers>"
                "</AutoDrive>"
            )

        path = tmp_path / "AutoDrive_config.xml"
        path.write_text(raw, encoding="utf-8")
        return path

    return _write
