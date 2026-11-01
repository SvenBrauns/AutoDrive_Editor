"""Settings → Maps: the imported maps, with re-import, remove, import from a mod zip and the
manual choice of the map for the open file."""

from typing import TYPE_CHECKING

from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from autodrive_editor.file_io.map_mod import BASE_MAP_SIZE
from autodrive_editor.i18n import tr
from autodrive_editor.terrain.game_picture import PICTURE_FOLDER
from autodrive_editor.terrain.map_cache import CachedMap, folder_size

if TYPE_CHECKING:
    from autodrive_editor.ui.map_import_controller import MapImportController


class MapsWidget(QWidget):
    def __init__(self, controller: "MapImportController", parent=None):
        super().__init__(parent)

        self.controller = controller
        self.maps: list[CachedMap] = []

        self.table = QTreeWidget(self)
        self.table.setHeaderLabels(
            [tr("Name"), tr("Mod"), tr("Size"), tr("Heightmap"), tr("Game picture")]
        )
        self.table.setRootIsDecorated(False)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.itemSelectionChanged.connect(self._update_buttons)

        self.reimport_button = QPushButton(tr("Re-import"), self)
        self.reimport_button.clicked.connect(lambda: self._run(controller.reimport))
        self.remove_button = QPushButton(tr("Remove"), self)
        self.remove_button.clicked.connect(lambda: self._run(controller.remove))
        import_button = QPushButton(tr("Import from mod zip…"), self)
        import_button.clicked.connect(lambda: (controller.import_map_mod(), self.refresh()))
        self.use_button = QPushButton(tr("Use this map for the open file"), self)
        self.use_button.clicked.connect(lambda: self._run(controller.use_for_open_file))

        buttons = QHBoxLayout()
        buttons.addWidget(self.reimport_button)
        buttons.addWidget(self.remove_button)
        buttons.addWidget(import_button)
        buttons.addStretch(1)

        layout = QVBoxLayout(self)
        layout.addWidget(self.table)
        layout.addLayout(buttons)
        layout.addWidget(self.use_button)

        self.refresh()

    def refresh(self):
        self.maps = self.controller.map_cache.maps()
        self.table.clear()

        for cached in self.maps:
            picture_bytes = folder_size(cached.directory / PICTURE_FOLDER)
            size_km = cached.map_scale * BASE_MAP_SIZE // 1000
            self.table.addTopLevelItem(
                QTreeWidgetItem(
                    [
                        cached.title,
                        cached.mod_name,
                        f"{size_km} km",
                        tr("yes") if cached.heightmap_path is not None else tr("no"),
                        f"{picture_bytes / 1e6:.0f} MB" if picture_bytes else "–",
                    ]
                )
            )

        for column in range(self.table.columnCount()):
            self.table.resizeColumnToContents(column)

        self._update_buttons()

    def selected_map(self) -> CachedMap | None:
        index = self.table.indexOfTopLevelItem(self.table.currentItem())

        return self.maps[index] if self.table.selectedItems() and index >= 0 else None

    def _run(self, action):
        cached = self.selected_map()

        if cached is not None:
            action(cached)
            self.refresh()

    def _update_buttons(self):
        cached = self.selected_map()
        file_open = self.controller.project_coordinator.config_source is not None

        self.reimport_button.setEnabled(cached is not None)
        self.remove_button.setEnabled(cached is not None)
        self.use_button.setEnabled(
            cached is not None and file_open and bool(cached.autodrive_names)
        )
