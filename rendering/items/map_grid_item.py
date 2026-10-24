import math

from PySide6.QtCore import (
    QLineF,
    QRectF,
    Qt
)
from PySide6.QtGui import (
    QColor,
    QPainter,
    QPen,
    QTransform
)
from PySide6.QtWidgets import (
    QGraphicsItem,
    QStyleOptionGraphicsItem,
    QWidget
)


class MapGridItem(QGraphicsItem):

    Z_VALUE = -900.0

    GRID_COLOR = QColor(
        255,
        255,
        255,
        90
    )

    MAX_VISIBLE_LINES = 4000

    def __init__(
        self,
        grid_rect: QRectF,
        spacing: float = 10.0,
        rotation_angle: float = 0.0
    ):
        super().__init__()

        self._grid_rect = QRectF(
            grid_rect
        )

        self._spacing = self._validate_spacing(
            spacing
        )

        self._rotation_angle = (
            self._normalize_rotation_angle(
                rotation_angle
            )
        )

        self._grid_pen = QPen(
            self.GRID_COLOR
        )

        self._grid_pen.setWidthF(
            1.0
        )

        self._grid_pen.setCosmetic(
            True
        )

        self.setZValue(
            self.Z_VALUE
        )

        self.setAcceptedMouseButtons(
            Qt.NoButton
        )

    @property
    def spacing(self) -> float:
        return self._spacing

    @property
    def rotation_angle(self) -> float:
        return self._rotation_angle

    def boundingRect(self) -> QRectF:
        return QRectF(
            self._grid_rect
        )

    def set_grid_rect(
        self,
        grid_rect: QRectF
    ):
        grid_rect = QRectF(
            grid_rect
        )

        if grid_rect == self._grid_rect:
            return

        self.prepareGeometryChange()

        self._grid_rect = grid_rect

        self.update()

    def set_spacing(
        self,
        spacing: float
    ):
        spacing = self._validate_spacing(
            spacing
        )

        if math.isclose(
            spacing,
            self._spacing,
            abs_tol=0.000001
        ):
            return

        self._spacing = spacing

        self.update()

    def set_rotation_angle(
        self,
        rotation_angle: float
    ):
        rotation_angle = (
            self._normalize_rotation_angle(
                rotation_angle
            )
        )

        if math.isclose(
            rotation_angle,
            self._rotation_angle,
            abs_tol=0.000001
        ):
            return

        self._rotation_angle = rotation_angle

        self.update()

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        widget: QWidget | None = None
    ):
        if (
            not self.isVisible()
            or self._grid_rect.isEmpty()
        ):
            return

        exposed_rect = (
            option.exposedRect
            .intersected(
                self._grid_rect
            )
        )

        if exposed_rect.isEmpty():
            return

        inverse_rotation = QTransform()

        inverse_rotation.rotate(
            -self._rotation_angle
        )

        grid_coordinate_rect = (
            inverse_rotation
            .mapRect(
                exposed_rect
            )
        )

        effective_spacing = (
            self._calculate_effective_spacing(
                grid_coordinate_rect
            )
        )

        vertical_lines = (
            self._create_vertical_lines(
                grid_coordinate_rect,
                effective_spacing
            )
        )

        horizontal_lines = (
            self._create_horizontal_lines(
                grid_coordinate_rect,
                effective_spacing
            )
        )

        painter.save()

        painter.setClipRect(
            self._grid_rect
        )

        painter.setPen(
            self._grid_pen
        )

        painter.rotate(
            self._rotation_angle
        )

        if vertical_lines:
            painter.drawLines(
                vertical_lines
            )

        if horizontal_lines:
            painter.drawLines(
                horizontal_lines
            )

        painter.restore()

    def _create_vertical_lines(
        self,
        grid_rect: QRectF,
        spacing: float
    ) -> list[QLineF]:
        first_x = (
            math.floor(
                grid_rect.left()
                / spacing
            )
            * spacing
        )

        lines = []

        current_x = first_x

        while current_x <= grid_rect.right():
            lines.append(
                QLineF(
                    current_x,
                    grid_rect.top(),
                    current_x,
                    grid_rect.bottom()
                )
            )

            current_x += spacing

        return lines

    def _create_horizontal_lines(
        self,
        grid_rect: QRectF,
        spacing: float
    ) -> list[QLineF]:
        first_z = (
            math.floor(
                grid_rect.top()
                / spacing
            )
            * spacing
        )

        lines = []

        current_z = first_z

        while current_z <= grid_rect.bottom():
            lines.append(
                QLineF(
                    grid_rect.left(),
                    current_z,
                    grid_rect.right(),
                    current_z
                )
            )

            current_z += spacing

        return lines

    def _calculate_effective_spacing(
        self,
        grid_rect: QRectF
    ) -> float:
        estimated_vertical_lines = (
            grid_rect.width()
            / self._spacing
        )

        estimated_horizontal_lines = (
            grid_rect.height()
            / self._spacing
        )

        estimated_line_count = (
            estimated_vertical_lines
            + estimated_horizontal_lines
        )

        if (
            estimated_line_count
            <= self.MAX_VISIBLE_LINES
        ):
            return self._spacing

        spacing_multiplier = math.ceil(
            estimated_line_count
            / self.MAX_VISIBLE_LINES
        )

        return (
            self._spacing
            * spacing_multiplier
        )

    @staticmethod
    def _validate_spacing(
        spacing: float
    ) -> float:
        spacing = float(
            spacing
        )

        if spacing <= 0.0:
            raise ValueError(
                "Der Rasterabstand muss "
                "größer als 0 sein."
            )

        return spacing

    @staticmethod
    def _normalize_rotation_angle(
        rotation_angle: float
    ) -> float:
        normalized_angle = (
            float(rotation_angle)
            % 360.0
        )

        if math.isclose(
            normalized_angle,
            360.0,
            abs_tol=0.000001
        ):
            return 0.0

        return normalized_angle