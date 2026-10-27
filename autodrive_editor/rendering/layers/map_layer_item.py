from PySide6.QtCore import QRectF, Qt
from PySide6.QtWidgets import QGraphicsItem

from autodrive_editor.rendering.display_style import DisplayStyle
from autodrive_editor.rendering.visibility import Visibility

# Room around the network for things drawn at a fixed size on screen, like marker names.
BOUNDS_MARGIN = 100.0


class MapLayerItem(QGraphicsItem):
    """One item that covers the whole network and draws a part of it. It paints only what
    lies in the exposed area, so there are no graphics items per node or connection."""

    def __init__(self, display_style: DisplayStyle, z_value: float):
        super().__init__()

        self.setFlag(QGraphicsItem.ItemUsesExtendedStyleOption, True)
        self.setAcceptedMouseButtons(Qt.NoButton)
        self.setZValue(z_value)

        self.display_style = display_style
        self.visibility = Visibility()
        self.bounds = QRectF()

    def boundingRect(self) -> QRectF:
        return self.bounds

    def set_network_bounds(self, network_bounds: QRectF):
        bounds = network_bounds.adjusted(
            -BOUNDS_MARGIN, -BOUNDS_MARGIN, BOUNDS_MARGIN, BOUNDS_MARGIN
        )

        if bounds == self.bounds:
            return

        self.prepareGeometryChange()
        self.bounds = bounds

    def set_display_style(self, display_style: DisplayStyle):
        self.display_style = display_style
        self.update()

    def set_visibility(self, visibility: Visibility):
        self.visibility = visibility
        self.update()
