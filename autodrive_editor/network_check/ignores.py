"""Check results the user chose to ignore, and checks switched off, kept
per network file.

Ignored entries are remembered by the positions of their nodes, not by
node ids: ids change when gaps are closed on save. An entry shows up
again once one of its nodes moves, or another node joins an overlapping
group.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path

from autodrive_editor.model.autodrive_data import AutoDriveData
from autodrive_editor.network_check.checks import ALL_CHECKS, CheckResults, problem_node_ids

Position = tuple[float, float, float]
IgnoreKey = tuple[str, frozenset[Position]]

# Route files store two decimals; small rounding differences after saving
# must not bring ignored entries back.
POSITION_DECIMALS = 2


@dataclass
class CheckIgnores:
    disabled_checks: set[str] = field(default_factory=set)
    ignored: set[IgnoreKey] = field(default_factory=set)

    @property
    def enabled_checks(self) -> set[str]:
        return set(ALL_CHECKS) - self.disabled_checks


def ignore_key(autodrive_data: AutoDriveData, kind: str, problem) -> IgnoreKey | None:
    """What an entry is remembered by. None if one of its nodes no longer
    exists."""

    positions = set()

    for node_id in problem_node_ids(kind, problem):
        node = autodrive_data.get_node(node_id)

        if node is None:
            return None

        positions.add(tuple(round(value, POSITION_DECIMALS) for value in (node.x, node.y, node.z)))

    return kind, frozenset(positions)


def ignore_keys(autodrive_data: AutoDriveData, results: CheckResults) -> set[IgnoreKey]:
    keys = {ignore_key(autodrive_data, kind, problem) for kind, problem in results.entries()}

    return keys - {None}


def split_ignored(
    autodrive_data: AutoDriveData, results: CheckResults, ignored: set[IgnoreKey]
) -> tuple[CheckResults, CheckResults]:
    """The results without the ignored entries, and the ignored entries."""

    shown = []
    hidden = []

    for kind, problem in results.entries():
        if ignore_key(autodrive_data, kind, problem) in ignored:
            hidden.append((kind, problem))
        else:
            shown.append((kind, problem))

    visible = CheckResults.from_entries(shown)

    if results.height_problems is None:
        visible = CheckResults(visible.overlapping_groups, visible.outside_node_ids, None)

    return visible, CheckResults.from_entries(hidden)


class IgnoreStore:
    """Reads and writes the ignores of all networks in one JSON file, by
    the path of the network file."""

    def __init__(self, file_path: Path):
        self.file_path = Path(file_path)

    def load(self, network_path: Path) -> CheckIgnores:
        entry = self._read().get(self._key(network_path))

        if entry is None:
            return CheckIgnores()

        return CheckIgnores(
            disabled_checks=set(entry.get("disabled_checks", [])) & set(ALL_CHECKS),
            ignored={
                (item["check"], frozenset(tuple(position) for position in item["positions"]))
                for item in entry.get("ignored", [])
            },
        )

    def save(self, network_path: Path, ignores: CheckIgnores):
        everything = self._read()
        key = self._key(network_path)

        if ignores.disabled_checks or ignores.ignored:
            everything[key] = {
                "disabled_checks": sorted(ignores.disabled_checks),
                "ignored": [
                    {"check": kind, "positions": [list(position) for position in positions]}
                    for kind, positions in ignores.ignored
                ],
            }
        else:
            everything.pop(key, None)

        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self.file_path.write_text(json.dumps(everything, indent=2), encoding="utf-8")

    def _read(self) -> dict:
        """All stored ignores. A missing or damaged file counts as empty."""

        try:
            return json.loads(self.file_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    @staticmethod
    def _key(network_path: Path) -> str:
        return str(Path(network_path).resolve())
