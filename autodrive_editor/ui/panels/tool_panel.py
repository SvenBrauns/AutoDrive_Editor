from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QDockWidget,
    QFrame,
    QGridLayout,
    QMainWindow,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)


class ToolGroup(QWidget):
    """A titled group of tool buttons that can be collapsed."""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)

        layout.setContentsMargins(0, 0, 0, 4)

        layout.setSpacing(2)

        self.header_button = QToolButton(self)

        self.header_button.setText(title)

        self.header_button.setCheckable(True)

        self.header_button.setChecked(True)

        self.header_button.setAutoRaise(True)

        self.header_button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)

        self.header_button.setArrowType(Qt.DownArrow)

        self.header_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.header_button.setStyleSheet("QToolButton { font-weight: bold; text-align: left; }")

        self.header_button.toggled.connect(self.set_expanded)

        layout.addWidget(self.header_button)

        self.content = QFrame(self)

        self.grid = QGridLayout(self.content)

        self.grid.setContentsMargins(4, 0, 4, 0)

        self.grid.setSpacing(2)

        layout.addWidget(self.content)

        self.extra_widgets: list[QWidget] = []

    @property
    def is_expanded(self) -> bool:
        return self.header_button.isChecked()

    def add_widget(self, widget: QWidget):
        """Adds a widget below the tool buttons, e.g. tool options. It is
        hidden together with the buttons."""

        self.layout().addWidget(widget)

        self.extra_widgets.append(widget)

    def set_expanded(self, expanded: bool):
        self.header_button.setChecked(expanded)

        self.header_button.setArrowType(Qt.DownArrow if expanded else Qt.RightArrow)

        self.content.setVisible(expanded)

        for widget in self.extra_widgets:
            widget.setVisible(expanded)


class ToolPanel(QDockWidget):
    """Left dock with one collapsible group per tool area, e.g. "Nodes"
    or "Marker". Tools are icon buttons in two columns; labels can be
    shown next to the icons."""

    ICON_SIZE = QSize(28, 28)

    def __init__(self, parent=None):
        super().__init__("Werkzeuge", parent)

        self.setObjectName("tool_panel")

        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)

        self.setFeatures(QDockWidget.DockWidgetClosable | QDockWidget.DockWidgetMovable)

        content = QWidget(self)

        self._layout = QVBoxLayout(content)

        self._layout.setContentsMargins(4, 4, 4, 4)

        self._layout.addStretch(1)

        self.setWidget(content)

        self.groups: dict[str, ToolGroup] = {}
        self.tool_buttons: dict[QAction, QToolButton] = {}

        self._labels_visible = False

    @property
    def labels_visible(self) -> bool:
        return self._labels_visible

    def add_tool_group(self, title: str, rows: list[tuple[QAction | None, ...]]) -> ToolGroup:
        """Adds a group. Each row holds up to two actions; None leaves
        a cell empty, e.g. for a tool that is planned but not built."""

        group = ToolGroup(title, self.widget())

        for row_index, row in enumerate(rows):
            for column_index, action in enumerate(row):
                if action is None:
                    continue

                button = self._create_button(action, group.content)

                group.grid.addWidget(button, row_index, column_index)

                self.tool_buttons[action] = button

        # Keep the stretch at the end so groups stack at the top.
        self._layout.insertWidget(self._layout.count() - 1, group)

        self.groups[title] = group

        return group

    def set_labels_visible(self, visible: bool):
        self._labels_visible = bool(visible)

        for button in self.tool_buttons.values():
            self._apply_button_style(button)

        # Update the group layouts now, so the minimum width below fits
        # the new button style.
        for group in self.groups.values():
            group.layout().activate()

        self._fit_width_to_content()

    def _fit_width_to_content(self):
        """Docks keep their width on their own, so widen the panel for
        labels and shrink it again without them. The width is taken
        from the buttons directly, since the layouts update their
        cached sizes only later."""

        main_window = self.parentWidget()

        if not isinstance(main_window, QMainWindow):
            return

        content_width = 0

        for group in self.groups.values():
            grid = group.grid
            margins = grid.contentsMargins()

            column_widths = [
                max(
                    (
                        grid.itemAtPosition(row, column).widget().sizeHint().width()
                        for row in range(grid.rowCount())
                        if grid.itemAtPosition(row, column) is not None
                    ),
                    default=0,
                )
                for column in range(grid.columnCount())
            ]

            group_width = (
                sum(column_widths)
                + grid.spacing() * max(len(column_widths) - 1, 0)
                + margins.left()
                + margins.right()
            )

            content_width = max(
                content_width,
                group_width,
                group.header_button.minimumSizeHint().width(),
                *(widget.sizeHint().width() for widget in group.extra_widgets),
            )

        outer_margins = self._layout.contentsMargins()
        frame_width = max(self.width() - self.widget().width(), 0)

        # The tool options make the window keep the panel's old minimum
        # width until its layout is updated, which would stop shrinking.
        main_window.layout().activate()

        main_window.resizeDocks(
            [self],
            [content_width + outer_margins.left() + outer_margins.right() + frame_width],
            Qt.Horizontal,
        )

    def _create_button(self, action: QAction, parent) -> QToolButton:
        button = QToolButton(parent)

        button.setDefaultAction(action)

        button.setIconSize(self.ICON_SIZE)

        button.setAutoRaise(True)

        self._apply_button_style(button)

        return button

    def _apply_button_style(self, button: QToolButton):
        if self._labels_visible:
            button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)

            button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        else:
            button.setToolButtonStyle(Qt.ToolButtonIconOnly)

            button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
