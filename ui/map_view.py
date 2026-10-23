from PySide6.QtWidgets import QGraphicsView


class MapView(QGraphicsView):

    def __init__(self):
        super().__init__()

        self.setDragMode(
            QGraphicsView.ScrollHandDrag
        )

        self.setTransformationAnchor(
            QGraphicsView.AnchorUnderMouse
        )

    def wheelEvent(self, event):

        zoom_factor = 1.15

        if event.angleDelta().y() > 0:
            self.scale(
                zoom_factor,
                zoom_factor
            )
        else:
            self.scale(
                1 / zoom_factor,
                1 / zoom_factor
            )