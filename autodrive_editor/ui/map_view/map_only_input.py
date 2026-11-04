from PySide6.QtCore import QEvent, QObject
from PySide6.QtWidgets import QWidget

# Input that could change something in the main window.
BLOCKED_EVENTS = {
    QEvent.Type.MouseButtonPress,
    QEvent.Type.MouseButtonRelease,
    QEvent.Type.MouseButtonDblClick,
    QEvent.Type.MouseMove,
    QEvent.Type.Wheel,
    QEvent.Type.KeyPress,
    QEvent.Type.KeyRelease,
    QEvent.Type.ShortcutOverride,
    QEvent.Type.Shortcut,
    QEvent.Type.ContextMenu,
    QEvent.Type.Close,
}

MAP_EVENTS = {
    QEvent.Type.MouseButtonPress,
    QEvent.Type.MouseButtonRelease,
    QEvent.Type.MouseButtonDblClick,
    QEvent.Type.MouseMove,
    QEvent.Type.Wheel,
}

KEY_EVENTS = {QEvent.Type.KeyPress, QEvent.Type.KeyRelease, QEvent.Type.ShortcutOverride}


class MapOnlyInput(QObject):
    """Application event filter for a dialog that is open beside the map: in the main window
    only the mouse on the map gets through, so the map can be moved, zoomed and rotated while
    menus, shortcuts, the other panels and closing the window are held back. Other windows, such
    as the dialog itself, are not affected. The keys in map_keys reach the map too."""

    def __init__(self, window: QWidget, map_view: QWidget, map_keys=(), parent=None):
        super().__init__(parent)

        self.window = window
        self.map_view = map_view
        self.map_keys = set(map_keys)

    def eventFilter(self, watched, event) -> bool:
        if event.type() not in BLOCKED_EVENTS:
            return False

        if isinstance(watched, QWidget):
            if watched.window() is not self.window:
                return False

            on_map = watched is self.map_view or self.map_view.isAncestorOf(watched)

            if on_map and event.type() in KEY_EVENTS and event.key() in self.map_keys:
                # An accepted override keeps a window shortcut on the key from taking it.
                if event.type() == QEvent.Type.ShortcutOverride:
                    event.accept()
                    return True

                return False

            return not (on_map and event.type() in MAP_EVENTS)

        # Shortcuts of the main window's actions go to the actions themselves.
        return event.type() == QEvent.Type.Shortcut
