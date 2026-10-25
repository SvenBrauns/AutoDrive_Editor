from enum import Enum, auto


class InteractionMode(Enum):
    """The active map tool. Exactly one is active at a time."""

    NAVIGATE = auto()
    SELECT = auto()
    CREATE_NODES = auto()
    CREATE_SUBPRIO_NODES = auto()
    TOGGLE_NODE_TYPE = auto()
    MOVE_NODES = auto()
    ROTATE_SELECTION = auto()
    DELETE_NODES = auto()
    CONNECT_REGULAR = auto()
    CONNECT_DUAL = auto()
    CONNECT_REVERSE = auto()
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
            InteractionMode.MOVE_NODES: "Nodes verschieben",
            InteractionMode.ROTATE_SELECTION: "Auswahl rotieren",
            InteractionMode.DELETE_NODES: "Nodes löschen",
            InteractionMode.CONNECT_REGULAR: "Verbinden (Regular)",
            InteractionMode.CONNECT_DUAL: "Verbinden (Dual)",
            InteractionMode.CONNECT_REVERSE: "Verbinden (Reverse)",
            InteractionMode.ADD_MARKER: "Marker hinzufügen",
            InteractionMode.EDIT_MARKER: "Marker bearbeiten",
            InteractionMode.MOVE_MARKER: "Marker verschieben",
            InteractionMode.DELETE_MARKER: "Marker löschen",
        }

        return display_names[self]
