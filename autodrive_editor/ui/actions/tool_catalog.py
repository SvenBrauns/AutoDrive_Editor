"""All map tools with their name, description, icon and shortcut, and
how they are grouped in the tool panel."""

from dataclasses import dataclass

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

from autodrive_editor.i18n import tr
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


# Undo/redo icons are recolored so it is obvious whether they can be
# used: blue when available, a grey close to the background when not.
# Qt's automatic disabled look of the dark grey icons was too similar.
HISTORY_ICON_SOURCE_COLOR = "#444"
HISTORY_ICON_COLOR = "#1f6fd1"
HISTORY_ICON_DISABLED_COLOR = "#cdcdcd"
HISTORY_ICON_DISABLED_DARK_COLOR = "#555555"
HISTORY_ICON_SIZES = (16, 20, 24, 32, 40, 48)


def history_icon(name: str, dark: bool = False) -> QIcon:
    svg = (TOOL_ICON_DIRECTORY / f"{name}.svg").read_text(encoding="utf-8")
    icon = QIcon()
    disabled_color = HISTORY_ICON_DISABLED_DARK_COLOR if dark else HISTORY_ICON_DISABLED_COLOR

    for mode, color in (
        (QIcon.Mode.Normal, HISTORY_ICON_COLOR),
        (QIcon.Mode.Disabled, disabled_color),
    ):
        renderer = QSvgRenderer(
            QByteArray(svg.replace(HISTORY_ICON_SOURCE_COLOR, color).encode("utf-8"))
        )

        for size in HISTORY_ICON_SIZES:
            pixmap = QPixmap(size, size)
            pixmap.fill(Qt.GlobalColor.transparent)

            painter = QPainter(pixmap)
            renderer.render(painter)
            painter.end()

            icon.addPixmap(pixmap, mode)

    return icon


def tool_tooltip(text: str, shortcut: str, description: str) -> str:
    shortcut = f" ({shortcut})" if shortcut else ""

    return f"<b>{text}</b>{shortcut}<br>{description}"


NAVIGATION_TOOL = ToolDefinition(
    InteractionMode.NAVIGATE, tr("Navigation"), tr("Move and rotate the map view"), "navigate", "N"
)

SELECTION_TOOL = ToolDefinition(
    InteractionMode.SELECT,
    tr("Selection"),
    tr("Select nodes by clicking or right-dragging"),
    "select",
    "A",
)

MOVE_TOOL = ToolDefinition(
    InteractionMode.MOVE_NODES,
    tr("Move"),
    tr("Move a node or the selection by left-dragging"),
    "move",
    "V",
)

CREATE_REGULAR_TOOL = ToolDefinition(
    InteractionMode.CREATE_NODES,
    tr("Create (Regular)"),
    tr("Left-click on free ground to create a regular node"),
    "create_regular",
    "E",
)

CREATE_SUBPRIO_TOOL = ToolDefinition(
    InteractionMode.CREATE_SUBPRIO_NODES,
    tr("Create (Subprio)"),
    tr("Left-click on free ground to create a subprio node"),
    "create_subprio",
    "Shift+E",
)

TOGGLE_TYPE_TOOL = ToolDefinition(
    InteractionMode.TOGGLE_NODE_TYPE,
    tr("Toggle type"),
    tr("Left-click a node or the selection to switch between regular and subprio"),
    "toggle_type",
    "T",
)

REVERSE_DIRECTION_TOOL = ToolDefinition(
    InteractionMode.REVERSE_DIRECTION,
    tr("Reverse direction"),
    tr(
        "Click a connection to reverse its direction; inside the selection, "
        "all connections of the selection are reversed"
    ),
    "reverse_direction",
    "U",
)

NODE_POSITION_TOOL = ToolDefinition(
    InteractionMode.EDIT_NODE_POSITION,
    tr("Enter position"),
    tr("Click a node and enter its position as numbers"),
    "node_position",
    "P",
)

ROTATE_TOOL = ToolDefinition(
    InteractionMode.ROTATE_SELECTION,
    tr("Rotate"),
    tr(
        "Rotate the selection around its center using the ring "
        "(Shift snaps, the arrow sets the step)"
    ),
    "rotate",
    "R",
)

DELETE_TOOL = ToolDefinition(
    InteractionMode.DELETE_NODES,
    tr("Delete"),
    tr("Left-click a node or the selection to delete it"),
    "delete",
    "L",
)

CONNECT_REGULAR_TOOL = ToolDefinition(
    InteractionMode.CONNECT_REGULAR,
    tr("Connect (Regular)"),
    tr("Click nodes one after another to connect them with regular connections"),
    "connect_regular",
    "1",
)

CONNECT_DUAL_TOOL = ToolDefinition(
    InteractionMode.CONNECT_DUAL,
    tr("Connect (Dual)"),
    tr("Click nodes one after another to connect them with dual connections"),
    "connect_dual",
    "2",
)

CONNECT_REVERSE_TOOL = ToolDefinition(
    InteractionMode.CONNECT_REVERSE,
    tr("Connect (Reverse)"),
    tr("Click nodes one after another to connect them with reverse connections"),
    "connect_reverse",
    "3",
)


ALIGN_HORIZONTAL_TOOL = ToolDefinition(
    InteractionMode.ALIGN_HORIZONTAL,
    tr("Align horizontally"),
    tr("Put the selection on the horizontal screen line through the clicked node"),
    "align_horizontal",
    "H",
)

ALIGN_VERTICAL_TOOL = ToolDefinition(
    InteractionMode.ALIGN_VERTICAL,
    tr("Align vertically"),
    tr("Put the selection on the vertical screen line through the clicked node"),
    "align_vertical",
    "J",
)

ALIGN_HEIGHT_TOOL = ToolDefinition(
    InteractionMode.ALIGN_HEIGHT,
    tr("Height like reference"),
    tr("Set the selection to the height of the clicked node"),
    "align_height",
    "Y",
)

HEIGHT_FROM_TERRAIN_TOOL = ToolDefinition(
    InteractionMode.HEIGHT_FROM_TERRAIN,
    tr("Height from heightmap"),
    tr("Click a node of the selection: each selected node gets the terrain height at its position"),
    "terrain_height",
    "Shift+Y",
)

LINE_TOOL = ToolDefinition(
    InteractionMode.DRAW_LINE,
    tr("Line"),
    tr("Click start and end: straight path with even node spacing"),
    "draw_line",
    "I",
)

BEZIER_TOOL = ToolDefinition(
    InteractionMode.DRAW_BEZIER,
    tr("Bézier curve"),
    tr("Click start and end, drag the handles, press Enter to create"),
    "draw_bezier",
    "B",
)

ARC_TOOL = ToolDefinition(
    InteractionMode.DRAW_ARC,
    tr("Arc"),
    tr("Click start and end, drag the handle on the arc, press Enter to create"),
    "draw_arc",
    "K",
)

ADD_MARKER_TOOL = ToolDefinition(
    InteractionMode.ADD_MARKER,
    tr("Add marker"),
    tr("Click a node and enter the name and group of the new marker"),
    "marker_add",
    "M",
)

EDIT_MARKER_TOOL = ToolDefinition(
    InteractionMode.EDIT_MARKER,
    tr("Edit marker"),
    tr("Click a node with a marker to change its name and group"),
    "marker_edit",
    "Shift+M",
)

MOVE_MARKER_TOOL = ToolDefinition(
    InteractionMode.MOVE_MARKER,
    tr("Move marker"),
    tr("Click a node with a marker, then the target node; name, group and number stay"),
    "marker_move",
    "Ctrl+M",
)

DELETE_MARKER_TOOL = ToolDefinition(
    InteractionMode.DELETE_MARKER,
    tr("Delete marker"),
    tr("Click a node with a marker to delete the marker; the node stays"),
    "marker_delete",
    "Ctrl+Shift+M",
)


# Title of the tool group that also holds the path options.
LINES_GROUP = tr("Lines")

# Tool groups in the left tool panel. Each row holds two tools:
# node actions on the left, connection actions on the right.
# None leaves a cell empty.
TOOL_GROUPS = (
    (
        tr("Nodes"),
        (
            (MOVE_TOOL, CONNECT_REGULAR_TOOL),
            (CREATE_REGULAR_TOOL, CONNECT_DUAL_TOOL),
            (CREATE_SUBPRIO_TOOL, CONNECT_REVERSE_TOOL),
            (TOGGLE_TYPE_TOOL, REVERSE_DIRECTION_TOOL),
            (ROTATE_TOOL, DELETE_TOOL),
            (NODE_POSITION_TOOL, None),
        ),
    ),
    (
        tr("Align"),
        (
            (ALIGN_HORIZONTAL_TOOL, ALIGN_VERTICAL_TOOL),
            (ALIGN_HEIGHT_TOOL, HEIGHT_FROM_TERRAIN_TOOL),
        ),
    ),
    (
        LINES_GROUP,
        (
            (LINE_TOOL, BEZIER_TOOL),
            (ARC_TOOL, None),
        ),
    ),
    (
        tr("Markers"),
        (
            (ADD_MARKER_TOOL, EDIT_MARKER_TOOL),
            (MOVE_MARKER_TOOL, DELETE_MARKER_TOOL),
        ),
    ),
)
