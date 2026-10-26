from collections.abc import Callable

from PySide6.QtCore import QObject, QPoint, Qt, Signal
from PySide6.QtGui import QPainterPath

from autodrive_editor.i18n import tr
from autodrive_editor.model.autodrive_data import AutoDriveData, NodeData
from autodrive_editor.rendering.scene_renderer import SceneRenderer
from autodrive_editor.selection.node_selection import NodeSelection
from autodrive_editor.ui.map_view.map_view import MapView
from autodrive_editor.ui.panels.node_info_formatter import NodeInfoFormatter


class SelectionCoordinator(QObject):
    """Applies clicks and area selections to the node selection and keeps the selection rings and
    the node info up to date.
    """

    NO_SELECTION_INFO = tr("No node selected")

    selection_info_changed = Signal(str)

    selection_state_changed = Signal()

    def __init__(
        self,
        view: MapView,
        renderer: SceneRenderer,
        node_selection: NodeSelection,
        node_info_formatter: NodeInfoFormatter,
        autodrive_data_provider: Callable[[], AutoDriveData | None],
        parent=None,
    ):
        super().__init__(parent)

        if not isinstance(view, MapView):
            raise TypeError("Invalid map view.")

        if not isinstance(renderer, SceneRenderer):
            raise TypeError("Invalid SceneRenderer.")

        if not isinstance(node_selection, NodeSelection):
            raise TypeError("Invalid NodeSelection.")

        if not isinstance(node_info_formatter, NodeInfoFormatter):
            raise TypeError("Invalid NodeInfoFormatter.")

        if not callable(autodrive_data_provider):
            raise TypeError("Invalid AutoDrive data provider.")

        self.view = view
        self.renderer = renderer

        self.node_selection = node_selection

        self.node_info_formatter = node_info_formatter

        self._autodrive_data_provider = autodrive_data_provider

        self.node_selection.selection_changed.connect(self._handle_selection_changed)

    @property
    def selected_node_ids(self) -> set[int]:
        return self.node_selection.selected_node_ids

    @property
    def primary_node_id(self) -> int | None:
        return self.node_selection.primary_node_id

    def show_node_info(self, node_data: NodeData):
        if not isinstance(node_data, NodeData):
            raise TypeError("Invalid node data.")

        self.node_selection.replace({node_data.node_id}, primary_node_id=node_data.node_id)

    def handle_click(self, view_position: QPoint, modifiers):
        clicked_node = self.get_node_at(view_position)

        control_pressed = bool(modifiers & Qt.ControlModifier)

        if clicked_node is None:
            if not control_pressed:
                self.node_selection.clear()

            return

        if control_pressed:
            self.node_selection.toggle(clicked_node.node_id)

        else:
            self.node_selection.replace(
                {clicked_node.node_id}, primary_node_id=(clicked_node.node_id)
            )

    def handle_area(self, selection_path: QPainterPath, modifiers):
        selected_nodes = self.renderer.get_nodes_in_selection_path(selection_path)

        selected_node_ids = {node_data.node_id for node_data in selected_nodes}

        primary_node_id = min(selected_node_ids) if selected_node_ids else None

        control_pressed = bool(modifiers & Qt.ControlModifier)

        if control_pressed:
            self.node_selection.toggle_many(selected_node_ids, primary_node_id=primary_node_id)

        else:
            self.node_selection.replace(selected_node_ids, primary_node_id=primary_node_id)

    def handle_area_preview(self, selection_path: QPainterPath, modifiers):
        preview_nodes = self.renderer.get_nodes_in_selection_path(selection_path)

        area_node_ids = {node_data.node_id for node_data in preview_nodes}

        current_node_ids = self.node_selection.selected_node_ids

        control_pressed = bool(modifiers & Qt.ControlModifier)

        if control_pressed:
            preview_node_ids = current_node_ids ^ area_node_ids

        else:
            preview_node_ids = area_node_ids

        self.renderer.set_selected_node_ids(preview_node_ids)

    def clear_area_preview(self):
        self.renderer.set_selected_node_ids(self.node_selection.selected_node_ids)

    def clear(self):
        self.node_selection.clear()

    def synchronize(self):
        selected_node_ids = self.node_selection.selected_node_ids

        primary_node_id = self.node_selection.primary_node_id

        self.renderer.set_selected_node_ids(selected_node_ids)

        self._emit_selection_info(selected_node_ids, primary_node_id)

        self.selection_state_changed.emit()

    def refresh_info(self):
        self._emit_selection_info(
            self.node_selection.selected_node_ids, self.node_selection.primary_node_id
        )

    def get_node_at(self, view_position: QPoint) -> NodeData | None:
        """The node drawn under the view position, if any."""

        scene_position = self.view.mapToScene(view_position)

        return self.renderer.get_node_at(
            scene_position.x(), scene_position.y(), self.view.zoom_level
        )

    def _handle_selection_changed(self, selected_node_ids, primary_node_id):
        self.renderer.set_selected_node_ids(selected_node_ids)

        self._emit_selection_info(selected_node_ids, primary_node_id)

        self.selection_state_changed.emit()

    def _emit_selection_info(self, selected_node_ids, primary_node_id):
        selection_info = self._format_selection_info(selected_node_ids, primary_node_id)

        self.selection_info_changed.emit(selection_info)

    def _format_selection_info(self, selected_node_ids, primary_node_id) -> str:
        if not selected_node_ids:
            return self.NO_SELECTION_INFO

        selection_count = len(selected_node_ids)

        autodrive_data = self._autodrive_data_provider()

        if autodrive_data is None or primary_node_id is None:
            return tr("{count} nodes selected", count=selection_count)

        primary_node = autodrive_data.get_node(primary_node_id)

        if primary_node is None:
            return tr("{count} nodes selected", count=selection_count)

        node_info_text = self.node_info_formatter.format_node_info(
            node_data=primary_node, autodrive_data=autodrive_data
        )

        if selection_count == 1:
            return node_info_text

        return (
            tr(
                "{count} nodes selected\nPrimary selection: {node}",
                count=selection_count,
                node=primary_node_id,
            )
            + f"\n\n{node_info_text}"
        )
