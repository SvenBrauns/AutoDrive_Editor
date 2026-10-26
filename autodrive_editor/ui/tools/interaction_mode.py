from enum import Enum, auto


class InteractionMode(Enum):
    """The active map tool. Exactly one is active at a time."""

    NAVIGATE = auto()
    SELECT = auto()
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
            InteractionMode.NAVIGATE: "Navigation",
            InteractionMode.SELECT: "Auswahl",
            InteractionMode.CREATE_NODES: "Nodes erstellen (Regular)",
            InteractionMode.CREATE_SUBPRIO_NODES: "Nodes erstellen (Subprio)",
            InteractionMode.TOGGLE_NODE_TYPE: "Node-Typ wechseln",
            InteractionMode.REVERSE_DIRECTION: "Richtung umkehren",
            InteractionMode.MOVE_NODES: "Nodes verschieben",
            InteractionMode.EDIT_NODE_POSITION: "Position eingeben",
            InteractionMode.ROTATE_SELECTION: "Auswahl rotieren",
            InteractionMode.DELETE_NODES: "Nodes löschen",
            InteractionMode.CONNECT_REGULAR: "Verbinden (Regular)",
            InteractionMode.CONNECT_DUAL: "Verbinden (Dual)",
            InteractionMode.CONNECT_REVERSE: "Verbinden (Reverse)",
            InteractionMode.ALIGN_HORIZONTAL: "Horizontal ausrichten",
            InteractionMode.ALIGN_VERTICAL: "Vertikal ausrichten",
            InteractionMode.ALIGN_HEIGHT: "Höhe wie Referenz",
            InteractionMode.HEIGHT_FROM_TERRAIN: "Höhe aus Heightmap",
            InteractionMode.DRAW_LINE: "Linie",
            InteractionMode.DRAW_BEZIER: "Bézierkurve",
            InteractionMode.DRAW_ARC: "Kreisbogen",
            InteractionMode.ADD_MARKER: "Marker hinzufügen",
            InteractionMode.EDIT_MARKER: "Marker bearbeiten",
            InteractionMode.MOVE_MARKER: "Marker verschieben",
            InteractionMode.DELETE_MARKER: "Marker löschen",
        }

        return display_names[self]
