import subprocess
import sys

import pytest

from autodrive_editor.game import game_process

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="reads the Windows task list")


def task_list(monkeypatch, output):
    result = subprocess.CompletedProcess([], 0, stdout=output)
    monkeypatch.setattr(game_process.subprocess, "run", lambda *args, **kwargs: result)


def test_game_process_is_found_in_the_task_list(monkeypatch):
    task_list(monkeypatch, '"explorer.exe","1"\n"FarmingSimulator2025Game.exe","2"\n')

    assert game_process.game_is_running()


def test_other_processes_are_not_the_game(monkeypatch):
    task_list(monkeypatch, '"explorer.exe","1"\n')

    assert not game_process.game_is_running()


def test_unreadable_task_list_counts_as_not_running(monkeypatch):
    def fail(*args, **kwargs):
        raise OSError

    monkeypatch.setattr(game_process.subprocess, "run", fail)

    assert not game_process.game_is_running()
