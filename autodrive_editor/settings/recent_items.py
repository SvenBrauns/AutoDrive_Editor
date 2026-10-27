"""The recently opened routes, savegames, XML files and projects."""

from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path

from autodrive_editor.i18n import tr

MAX_RECENT_ITEMS = 5


class RecentKind(Enum):
    ROUTE = "route"
    SAVEGAME = "savegame"
    XML = "xml"
    PROJECT = "project"


KIND_NAMES = {
    RecentKind.ROUTE: tr("Route"),
    RecentKind.SAVEGAME: tr("Savegame"),
    RecentKind.XML: tr("XML file"),
    RecentKind.PROJECT: tr("Project"),
}


@dataclass(frozen=True)
class RecentItem:
    """An opened file. Routes and savegames keep their name and map, so
    they open the same way as from their list."""

    kind: RecentKind
    path: str
    name: str
    map_name: str | None = None

    @property
    def label(self) -> str:
        return f"{self.name} – {KIND_NAMES[self.kind]}"

    def to_dict(self) -> dict:
        return {**asdict(self), "kind": self.kind.value}

    @classmethod
    def from_dict(cls, values: dict) -> "RecentItem":
        return cls(
            RecentKind(values["kind"]), values["path"], values["name"], values.get("map_name")
        )


def with_recent_item(items: list[RecentItem], item: RecentItem) -> list[RecentItem]:
    """The list with the item at the top, without an older entry for the same
    file, and at most MAX_RECENT_ITEMS long."""

    others = [old for old in items if not _same_file(old.path, item.path)]

    return [item, *others][:MAX_RECENT_ITEMS]


def without_recent_item(items: list[RecentItem], item: RecentItem) -> list[RecentItem]:
    return [old for old in items if not _same_file(old.path, item.path)]


def _same_file(a: str, b: str) -> bool:
    return Path(a).resolve() == Path(b).resolve()
