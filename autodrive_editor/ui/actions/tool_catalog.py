"""All map tools with their name, description, icon and shortcut, and
how they are grouped in the tool panel."""

from dataclasses import dataclass

from PySide6.QtGui import QIcon

from autodrive_editor.paths import TOOL_ICON_DIRECTORY
from autodrive_editor.ui.tools.interaction_mode import InteractionMode


@dataclass(frozen=True)
class ToolDefinition:
    """How a tool appears in the editor."""

    interaction_mode: InteractionMode
    text: str
    description: str
    icon: str
    shortcut: str


def tool_icon(name: str) -> QIcon:
    return QIcon(str(TOOL_ICON_DIRECTORY / f"{name}.svg"))


def tool_tooltip(text: str, shortcut: str, description: str) -> str:
    return f"<b>{text}</b> ({shortcut})<br>{description}"


NAVIGATION_TOOL = ToolDefinition(
    InteractionMode.NAVIGATE, "Navigation", "Kartenansicht verschieben und drehen", "navigate", "N"
)

SELECTION_TOOL = ToolDefinition(
    InteractionMode.SELECT, "Auswahl", "Nodes per Klick oder Rechtsziehen auswählen", "select", "A"
)

MOVE_TOOL = ToolDefinition(
    InteractionMode.MOVE_NODES,
    "Verschieben",
    "Node oder Auswahl per Linkes Ziehen verschieben",
    "move",
    "V",
)

CREATE_REGULAR_TOOL = ToolDefinition(
    InteractionMode.CREATE_NODES,
    "Erstellen (Regular)",
    "Per Linksklick auf freie Fläche eine Regular-Node erstellen",
    "create_regular",
    "E",
)

CREATE_SUBPRIO_TOOL = ToolDefinition(
    InteractionMode.CREATE_SUBPRIO_NODES,
    "Erstellen (Subprio)",
    "Per Linksklick auf freie Fläche eine Subprio-Node erstellen",
    "create_subprio",
    "Shift+E",
)

TOGGLE_TYPE_TOOL = ToolDefinition(
    InteractionMode.TOGGLE_NODE_TYPE,
    "Typ wechseln",
    "Node oder Auswahl per Linksklick zwischen Regular und Subprio umschalten",
    "toggle_type",
    "T",
)

ROTATE_TOOL = ToolDefinition(
    InteractionMode.ROTATE_SELECTION,
    "Rotieren",
    "Auswahl am Ring um ihren Mittelpunkt drehen (Umschalt: 15°-Schritte)",
    "rotate",
    "R",
)

DELETE_TOOL = ToolDefinition(
    InteractionMode.DELETE_NODES,
    "Löschen",
    "Node oder Auswahl per Linksklick löschen",
    "delete",
    "L",
)

CONNECT_REGULAR_TOOL = ToolDefinition(
    InteractionMode.CONNECT_REGULAR,
    "Verbinden (Regular)",
    "Nodes nacheinander anklicken, um sie mit Regular-Connections zu verbinden",
    "connect_regular",
    "1",
)

CONNECT_DUAL_TOOL = ToolDefinition(
    InteractionMode.CONNECT_DUAL,
    "Verbinden (Dual)",
    "Nodes nacheinander anklicken, um sie mit Dual-Connections zu verbinden",
    "connect_dual",
    "2",
)

CONNECT_REVERSE_TOOL = ToolDefinition(
    InteractionMode.CONNECT_REVERSE,
    "Verbinden (Reverse)",
    "Nodes nacheinander anklicken, um sie mit Reverse-Connections zu verbinden",
    "connect_reverse",
    "3",
)


# Tool groups in the left tool panel. Each row holds two tools:
# node actions on the left, connection actions on the right.
# None leaves a cell empty.
TOOL_GROUPS = (
    (
        "Nodes",
        (
            (MOVE_TOOL, CONNECT_REGULAR_TOOL),
            (CREATE_REGULAR_TOOL, CONNECT_DUAL_TOOL),
            (CREATE_SUBPRIO_TOOL, CONNECT_REVERSE_TOOL),
            (TOGGLE_TYPE_TOOL, None),
            (ROTATE_TOOL, DELETE_TOOL),
        ),
    ),
)
