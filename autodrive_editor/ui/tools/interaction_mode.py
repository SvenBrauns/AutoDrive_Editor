from enum import Enum, auto

from autodrive_editor.i18n import tr


class InteractionMode(Enum):
    """The active map tool. Exactly one is active at a time."""

    NAVIGATE = auto()
    SELECT = auto()
    PARKING_SPOTS = auto()
    CREATE_NODES = auto()
    CREATE_SUBPRIO_NODES = auto()
    TOGGLE_NODE_TYPE = auto()
    REVERSE_DIRECTION = auto()
    MOVE_NODES = auto()
    EDIT_NODE_POSITION = auto()
    ROTATE_SELECTION = auto()
    DELETE_NODES = auto()
    CONNECT_REGULAR = auto()
    CONNECT_DUAL = auto()
    CONNECT_REVERSE = auto()
    ALIGN_HORIZONTAL = auto()
    ALIGN_VERTICAL = auto()
    ALIGN_HEIGHT = auto()
    HEIGHT_FROM_TERRAIN = auto()
    DRAW_LINE = auto()
    DRAW_BEZIER = auto()
    DRAW_ARC = auto()
    ADD_MARKER = auto()
    EDIT_MARKER = auto()
    MOVE_MARKER = auto()
    DELETE_MARKER = auto()

    @property
    def display_name(self) -> str:
        display_names = {
            InteractionMode.NAVIGATE: tr("Navigation"),
            InteractionMode.SELECT: tr("Selection"),
            InteractionMode.PARKING_SPOTS: tr("Parking spots"),
            InteractionMode.CREATE_NODES: tr("Create nodes (Regular)"),
            InteractionMode.CREATE_SUBPRIO_NODES: tr("Create nodes (Subprio)"),
            InteractionMode.TOGGLE_NODE_TYPE: tr("Toggle node type"),
            InteractionMode.REVERSE_DIRECTION: tr("Reverse direction"),
            InteractionMode.MOVE_NODES: tr("Move nodes"),
            InteractionMode.EDIT_NODE_POSITION: tr("Enter position"),
            InteractionMode.ROTATE_SELECTION: tr("Rotate selection"),
            InteractionMode.DELETE_NODES: tr("Delete nodes"),
            InteractionMode.CONNECT_REGULAR: tr("Connect (Regular)"),
            InteractionMode.CONNECT_DUAL: tr("Connect (Dual)"),
            InteractionMode.CONNECT_REVERSE: tr("Connect (Reverse)"),
            InteractionMode.ALIGN_HORIZONTAL: tr("Align horizontally"),
            InteractionMode.ALIGN_VERTICAL: tr("Align vertically"),
            InteractionMode.ALIGN_HEIGHT: tr("Height like reference"),
            InteractionMode.HEIGHT_FROM_TERRAIN: tr("Height from heightmap"),
            InteractionMode.DRAW_LINE: tr("Line"),
            InteractionMode.DRAW_BEZIER: tr("Bézier curve"),
            InteractionMode.DRAW_ARC: tr("Arc"),
            InteractionMode.ADD_MARKER: tr("Add marker"),
            InteractionMode.EDIT_MARKER: tr("Edit marker"),
            InteractionMode.MOVE_MARKER: tr("Move marker"),
            InteractionMode.DELETE_MARKER: tr("Delete marker"),
        }

        return display_names[self]
