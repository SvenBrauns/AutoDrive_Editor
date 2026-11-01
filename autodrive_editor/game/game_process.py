"""Whether Farming Simulator 25 is running, read from the Windows task list."""

import subprocess
import sys

# The launcher and the game itself (FarmingSimulator2025Game.exe) both start with this.
PROCESS_PREFIX = "farmingsimulator2025"


def game_is_running() -> bool:
    """True if a FarmingSimulator2025 process runs. False off Windows or if the task list
    cannot be read."""

    if sys.platform != "win32":
        return False

    try:
        output = subprocess.run(
            ["tasklist", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return False

    return any(line.strip('"').lower().startswith(PROCESS_PREFIX) for line in output.splitlines())
