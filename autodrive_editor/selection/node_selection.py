from PySide6.QtCore import QObject, Signal


class NodeSelection(QObject):
    """Which nodes are selected and which of them is the primary one, shown in the info panel."""

    selection_changed = Signal(object, object)

    def __init__(self):
        super().__init__()

        self._selected_node_ids: set[int] = set()
        self._primary_node_id: int | None = None

    @property
    def selected_node_ids(self) -> set[int]:
        return set(self._selected_node_ids)

    @property
    def primary_node_id(self) -> int | None:
        return self._primary_node_id

    def replace(self, node_ids, primary_node_id=None):
        normalized_ids = self._normalize_node_ids(node_ids)

        normalized_primary_id = self._determine_primary_node_id(normalized_ids, primary_node_id)

        self._apply_selection(normalized_ids, normalized_primary_id)

    def add(self, node_ids, primary_node_id=None):
        normalized_ids = self._normalize_node_ids(node_ids)

        if not normalized_ids:
            return

        updated_ids = self._selected_node_ids | normalized_ids

        normalized_primary_id = self._determine_primary_node_id(updated_ids, primary_node_id)

        self._apply_selection(updated_ids, normalized_primary_id)

    def toggle(self, node_id: int):
        node_id = int(node_id)

        updated_ids = set(self._selected_node_ids)

        if node_id in updated_ids:
            updated_ids.remove(node_id)

            if self._primary_node_id == node_id:
                primary_node_id = min(updated_ids) if updated_ids else None

            else:
                primary_node_id = self._primary_node_id

        else:
            updated_ids.add(node_id)

            primary_node_id = node_id

        self._apply_selection(updated_ids, primary_node_id)

    def toggle_many(self, node_ids, primary_node_id=None):
        normalized_ids = self._normalize_node_ids(node_ids)

        if not normalized_ids:
            return

        updated_ids = self._selected_node_ids ^ normalized_ids

        requested_primary_id = int(primary_node_id) if primary_node_id is not None else None

        if requested_primary_id is not None and requested_primary_id in updated_ids:
            updated_primary_id = requested_primary_id

        elif self._primary_node_id in updated_ids:
            updated_primary_id = self._primary_node_id

        else:
            updated_primary_id = min(updated_ids) if updated_ids else None

        self._apply_selection(updated_ids, updated_primary_id)

    def remove(self, node_ids):
        """Deselects the given nodes, e.g. after they were deleted."""

        updated_ids = self._selected_node_ids - self._normalize_node_ids(node_ids)

        self._apply_selection(
            updated_ids, self._determine_primary_node_id(updated_ids, self._primary_node_id)
        )

    def clear(self):
        self._apply_selection(set(), None)

    def _apply_selection(self, node_ids: set[int], primary_node_id: int | None):
        if node_ids == self._selected_node_ids and primary_node_id == self._primary_node_id:
            return

        self._selected_node_ids = set(node_ids)

        self._primary_node_id = primary_node_id

        self.selection_changed.emit(self.selected_node_ids, self._primary_node_id)

    @staticmethod
    def _normalize_node_ids(node_ids) -> set[int]:
        return {int(node_id) for node_id in node_ids if int(node_id) > 0}

    @staticmethod
    def _determine_primary_node_id(node_ids: set[int], requested_primary_node_id) -> int | None:
        if not node_ids:
            return None

        if requested_primary_node_id is not None:
            requested_primary_node_id = int(requested_primary_node_id)

            if requested_primary_node_id in node_ids:
                return requested_primary_node_id

        return min(node_ids)
