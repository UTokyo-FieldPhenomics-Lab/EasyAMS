"""Batch remove-items dialog for Metashape chunks."""

from typing import Dict, List

from PySide2.QtCore import Qt
from PySide2.QtGui import QColor, QBrush
from PySide2.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
)

import Metashape


ITEM_TYPES = (
    "Cameras",
    "Masks",
    "Markers",
    "Thumbnails",
    "Scale Bars",
    "Shapes",
    "Depth Maps",
    "Point Clouds",
    "Laser Scans",
    "Models",
    "Textures",
    "Tiled Models",
    "Elevation Models",
    "Orthomosaics",
    "Tie Points",
)


def _count_sequence(value) -> int:
    """Count sequence-like values safely.

    Parameters
    ----------
    value : object
        Sequence-like object or ``None``.

    Returns
    -------
    int
        Sequence length, ``1`` for truthy non-sequences, else ``0``.
    """
    if value is None:
        return 0
    try:
        return len(value)
    except Exception:
        return 1 if bool(value) else 0


def get_chunk_type_counts(chunk) -> Dict[str, int]:
    """Collect item counts for one chunk.

    Parameters
    ----------
    chunk : object
        Metashape chunk-like object.

    Returns
    -------
    Dict[str, int]
        Per-item-type count map for display filtering.
    """
    model = getattr(chunk, "model", None)
    textures = getattr(model, "textures", None) if model is not None else None
    return {
        "Cameras": _count_sequence(getattr(chunk, "cameras", None)),
        "Masks": _count_sequence(getattr(chunk, "masks", None)),
        "Markers": _count_sequence(getattr(chunk, "markers", None)),
        "Thumbnails": _count_sequence(getattr(chunk, "thumbnails", None)),
        "Scale Bars": _count_sequence(getattr(chunk, "scalebars", None)),
        "Shapes": _count_sequence(getattr(chunk, "shapes", None)),
        "Depth Maps": _count_sequence(getattr(chunk, "depth_maps", None)),
        "Point Clouds": _count_sequence(getattr(chunk, "point_cloud", None)),
        "Laser Scans": _count_sequence(getattr(chunk, "laser_scans", None)),
        "Models": _count_sequence(model),
        "Textures": _count_sequence(textures),
        "Tiled Models": _count_sequence(getattr(chunk, "tiled_model", None)),
        "Elevation Models": _count_sequence(getattr(chunk, "elevation", None)),
        "Orthomosaics": _count_sequence(getattr(chunk, "orthomosaic", None)),
        "Tie Points": _count_sequence(getattr(chunk, "tie_points", None)),
    }


def build_preview_for_chunk(chunk) -> List[str]:
    """Build preview labels for one chunk in ``Type (count)`` format.

    Parameters
    ----------
    chunk : object
        Metashape chunk-like object.

    Returns
    -------
    List[str]
        Preview labels for item types present in the chunk.
    """
    counts = get_chunk_type_counts(chunk)
    labels: List[str] = []
    for item_type in ITEM_TYPES:
        count = counts.get(item_type, 0)
        if count <= 0:
            continue
        labels.append(f"{item_type} ({count})")
    return labels


def _get_chunks() -> List[object]:
    """Get chunk list from current document safely."""
    document = getattr(Metashape.app, "document", None)
    if document is None:
        return []
    return list(getattr(document, "chunks", []))


def _clear_sequence_attr(chunk, attr_name: str) -> None:
    """Clear a sequence-like chunk attribute safely."""
    items = getattr(chunk, attr_name, None)
    if items is None:
        return
    try:
        items.clear()
        return
    except Exception:
        pass
    try:
        del items[:]
        return
    except Exception:
        pass
    try:
        setattr(chunk, attr_name, [])
    except Exception:
        return


def _remove_shapes_by_group(shapes_obj) -> None:
    """Remove all shapes first, then remove shape groups."""
    remove_fn = getattr(shapes_obj, "remove", None)
    if not callable(remove_fn):
        return
    groups = list(getattr(shapes_obj, "groups", []))
    for group in groups:
        try:
            shapes = [
                shape
                for shape in list(shapes_obj)
                if getattr(shape, "group", None) == group
            ]
        except Exception:
            shapes = []
        for shape in shapes:
            try:
                remove_fn(shape)
            except Exception:
                continue
        try:
            remove_fn(group)
        except Exception:
            continue
    try:
        leftovers = list(shapes_obj)
    except Exception:
        leftovers = []
    for shape in leftovers:
        try:
            remove_fn(shape)
        except Exception:
            continue


def _clear_object_attr(chunk, attr_name: str) -> None:
    """Set an object-like chunk attribute to ``None``."""
    if not hasattr(chunk, attr_name):
        return
    setattr(chunk, attr_name, None)


def _delete_cameras(chunk) -> None:
    """Delete cameras and camera groups in one chunk."""
    _clear_sequence_attr(chunk, "cameras")
    _clear_sequence_attr(chunk, "camera_groups")


def _delete_markers(chunk) -> None:
    """Delete markers in one chunk."""
    _clear_sequence_attr(chunk, "markers")


def _delete_shapes(chunk) -> None:
    """Delete shapes in one chunk."""
    shapes_obj = getattr(chunk, "shapes", None)
    if shapes_obj is None:
        return
    _remove_shapes_by_group(shapes_obj)
    chunk_remove = getattr(chunk, "remove", None)
    if not callable(chunk_remove):
        return
    try:
        chunk_remove(shapes_obj)
    except Exception:
        try:
            chunk_remove([shapes_obj])
        except Exception:
            return


def _delete_tie_points(chunk) -> None:
    """Delete tie points reference in one chunk."""
    _clear_object_attr(chunk, "tie_points")


def _delete_point_cloud(chunk) -> None:
    """Delete point cloud reference in one chunk."""
    _clear_object_attr(chunk, "point_cloud")


def _delete_model(chunk) -> None:
    """Delete model reference in one chunk."""
    _clear_object_attr(chunk, "model")


def _delete_elevation(chunk) -> None:
    """Delete elevation reference in one chunk."""
    _clear_object_attr(chunk, "elevation")


def _delete_orthomosaic(chunk) -> None:
    """Delete orthomosaic reference in one chunk."""
    _clear_object_attr(chunk, "orthomosaic")


def _delete_depth_maps(chunk) -> None:
    """Delete depth maps reference in one chunk."""
    _clear_object_attr(chunk, "depth_maps")


DELETE_HANDLER_BY_TYPE = {
    "Cameras": _delete_cameras,
    "Markers": _delete_markers,
    "Shapes": _delete_shapes,
    "Tie Points": _delete_tie_points,
    "Point Clouds": _delete_point_cloud,
    "Models": _delete_model,
    "Elevation Models": _delete_elevation,
    "Orthomosaics": _delete_orthomosaic,
    "Depth Maps": _delete_depth_maps,
}


def apply_type_deletion(chunk, selected_types: List[str]) -> None:
    """Apply type-based deletion handlers on one chunk.

    Parameters
    ----------
    chunk : object
        Metashape chunk-like object.
    selected_types : List[str]
        Selected item type names from UI.
    """
    for item_type in selected_types:
        handler = DELETE_HANDLER_BY_TYPE.get(item_type)
        if handler is None:
            continue
        handler(chunk)


def build_confirmation_message(
    selected_chunk_keys: List[int], selected_types: List[str], total_nodes: int = 0
) -> str:
    """Build confirmation dialog message with optional warnings.

    Parameters
    ----------
    selected_chunk_keys : List[int]
        Selected chunk keys for deletion.
    selected_types : List[str]
        Selected item types for deletion.
    total_nodes : int, default=0
        Total impacted preview nodes.

    Returns
    -------
    str
        Rich-text confirmation message.
    """
    lines = [
        f"Chunks: {len(selected_chunk_keys)}",
        f"Types: {', '.join(selected_types)}",
        f"Impacted nodes: {total_nodes}",
    ]
    if "Shapes" in selected_types:
        lines.append(
            "<span style='color:#cc2222;'><b>Warning:</b> "
            "Metashape may keep a default empty shape layer due to API limits.</span>"
        )
    return "<br/>".join(lines)


def get_metashape_version() -> str:
    """Get the current Metashape version string."""
    return getattr(Metashape.app, "version", "0.0.0")


def _version_key(version: str) -> List[int]:
    """Convert semantic version string to comparable integer list."""
    parts = version.split(".")
    return [int(part) for part in parts[:3] if part.isdigit()]


def _fallback_capabilities(version: str) -> Dict[str, bool]:
    """Return fallback remove-item capability map for one version."""
    supports = {item_type: False for item_type in ITEM_TYPES}
    supports["Cameras"] = True
    supports["Markers"] = True
    supports["Scale Bars"] = True
    supports["Shapes"] = True

    if _version_key(version) >= [2, 1, 3]:
        supports["Depth Maps"] = True
        supports["Point Clouds"] = True
        supports["Models"] = True
        supports["Tiled Models"] = True
        supports["Elevation Models"] = True
        supports["Orthomosaics"] = True

    return supports


def resolve_dialog_capabilities() -> Dict[str, bool]:
    """Resolve remove-item capabilities for current version."""
    try:
        from easyams.api_capability import resolve_capabilities_for_current_version

        resolved = resolve_capabilities_for_current_version()
        return resolved.get("supports", {})
    except Exception:
        return _fallback_capabilities(get_metashape_version())


class BatchRemoveItemsDialog(QDialog):
    """Dialog for selecting item types and chunks to remove items from."""

    def __init__(self, parent=None):
        """Initialize dialog widgets and default state."""
        super().__init__(parent)
        self.setModal(True)
        self.setWindowTitle("Batch Remove Items")
        self.resize(720, 560)

        self.item_list = QListWidget()
        self.item_list.setSelectionMode(QListWidget.MultiSelection)
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabel("Chunks -> Item Types")

        self._supported_types = resolve_dialog_capabilities()
        self._chunks = _get_chunks()
        self._chunk_counts = {
            getattr(chunk, "key", index): get_chunk_type_counts(chunk)
            for index, chunk in enumerate(self._chunks)
        }
        self._visible_item_types = self._collect_visible_item_types()

        self._build_ui()
        self._populate_item_types()
        self._populate_chunk_tree()
        self._connect_preview_signals()
        self._refresh_preview()

    def _connect_preview_signals(self) -> None:
        """Connect UI events to realtime preview updates."""
        self.item_list.itemSelectionChanged.connect(self._refresh_preview)
        self.tree_widget.itemChanged.connect(self._on_tree_item_changed)

    def _collect_visible_item_types(self) -> List[str]:
        """Collect item types that appear in any chunk."""
        if not self._chunk_counts:
            return list(ITEM_TYPES)
        visible: List[str] = []
        for item_type in ITEM_TYPES:
            if any(
                counts.get(item_type, 0) > 0 for counts in self._chunk_counts.values()
            ):
                visible.append(item_type)
        return visible

    def _build_ui(self) -> None:
        """Build dialog layout in required control order."""
        layout = QVBoxLayout()
        layout.addWidget(self.item_list)

        tree_controls = QHBoxLayout()
        for text, callback in (
            ("Expand", self.tree_widget.expandAll),
            ("Collapse", self.tree_widget.collapseAll),
            ("Select All", self._select_all_chunks),
            ("Clear", self._clear_all_chunks),
        ):
            button = QPushButton(text)
            button.clicked.connect(callback)
            tree_controls.addWidget(button)
        tree_controls.addStretch()
        layout.addLayout(tree_controls)
        layout.addWidget(self.tree_widget)

        actions = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        execute_btn = QPushButton("Execute")
        execute_btn.clicked.connect(self.execute_remove)
        actions.addStretch()
        actions.addWidget(cancel_btn)
        actions.addWidget(execute_btn)
        layout.addLayout(actions)
        self.setLayout(layout)

    def _populate_item_types(self) -> None:
        """Fill item list and disable unsupported item types."""
        self.item_list.clear()
        for item_type in self._visible_item_types:
            item = QListWidgetItem(item_type)
            if not self._supported_types.get(item_type, False):
                item.setFlags(item.flags() & ~Qt.ItemIsEnabled)
            self.item_list.addItem(item)

    def _populate_chunk_tree(self) -> None:
        """Fill chunk tree with unchecked chunk and item-type nodes."""
        self.tree_widget.clear()
        for index, chunk in enumerate(self._chunks):
            chunk_key = getattr(chunk, "key", index)
            counts = self._chunk_counts.get(chunk_key, {})
            preview_labels = build_preview_for_chunk(chunk)
            chunk_item = QTreeWidgetItem(self.tree_widget)
            chunk_item.setText(0, getattr(chunk, "label", "Unnamed Chunk"))
            chunk_item.setData(0, Qt.UserRole, chunk_key)
            chunk_item.setFlags(chunk_item.flags() | Qt.ItemIsUserCheckable)
            chunk_item.setCheckState(0, Qt.Unchecked)
            for label in preview_labels:
                item_type = self._extract_type_name(label)
                if item_type not in self._visible_item_types:
                    continue
                if counts.get(item_type, 0) <= 0:
                    continue
                type_item = QTreeWidgetItem(chunk_item)
                type_item.setText(0, label)

    def _on_tree_item_changed(self, item: QTreeWidgetItem, _column: int) -> None:
        """Refresh preview when chunk check states change."""
        if item.parent() is not None:
            return
        self._refresh_preview()

    def _extract_type_name(self, text: str) -> str:
        """Extract base type name from preview text label."""
        if " (" not in text:
            return text
        return text.split(" (", 1)[0]

    def _refresh_preview(self) -> None:
        """Apply realtime delete preview style to tree nodes."""
        selected_types = set(self.get_selected_item_types())
        root = self.tree_widget.invisibleRootItem()
        for index in range(root.childCount()):
            chunk_item = root.child(index)
            chunk_checked = chunk_item.checkState(0) == Qt.Checked
            for child_index in range(chunk_item.childCount()):
                type_item = chunk_item.child(child_index)
                item_type = self._extract_type_name(type_item.text(0))
                is_target = chunk_checked and item_type in selected_types
                self._set_preview_style(type_item, is_target)

    def _set_preview_style(self, item: QTreeWidgetItem, strike_out: bool) -> None:
        """Set red strike style for deletion targets."""
        font = item.font(0)
        font.setStrikeOut(strike_out)
        item.setFont(0, font)
        color = QColor("#cc2222") if strike_out else QColor("#000000")
        item.setForeground(0, QBrush(color))

    def _select_all_chunks(self) -> None:
        """Check all top-level chunk nodes."""
        root = self.tree_widget.invisibleRootItem()
        for index in range(root.childCount()):
            root.child(index).setCheckState(0, Qt.Checked)

    def _clear_all_chunks(self) -> None:
        """Uncheck all top-level chunk nodes."""
        root = self.tree_widget.invisibleRootItem()
        for index in range(root.childCount()):
            root.child(index).setCheckState(0, Qt.Unchecked)

    def get_selected_item_types(self) -> List[str]:
        """Get selected item types from list widget."""
        return [item.text() for item in self.item_list.selectedItems()]

    def get_selected_chunk_keys(self) -> List[int]:
        """Get checked chunk keys from tree root nodes."""
        selected_keys: List[int] = []
        root = self.tree_widget.invisibleRootItem()
        for index in range(root.childCount()):
            chunk_item = root.child(index)
            if chunk_item.checkState(0) != Qt.Checked:
                continue
            selected_keys.append(chunk_item.data(0, Qt.UserRole))
        return selected_keys

    def is_item_type_enabled(self, item_type: str) -> bool:
        """Return whether a named item type is enabled."""
        for index in range(self.item_list.count()):
            item = self.item_list.item(index)
            if item.text() != item_type:
                continue
            return bool(item.flags() & Qt.ItemIsEnabled)
        return False

    def _get_chunk_by_key(self, chunk_key):
        """Get chunk object from cached chunk list by key."""
        for index, chunk in enumerate(self._chunks):
            key = getattr(chunk, "key", index)
            if key != chunk_key:
                continue
            return chunk
        return None

    def _collect_target_count(
        self, selected_chunk_keys: List[int], selected_types: List[str]
    ) -> int:
        """Count total impacted type nodes for confirmation summary."""
        total = 0
        for chunk_key in selected_chunk_keys:
            counts = self._chunk_counts.get(chunk_key, {})
            for item_type in selected_types:
                if counts.get(item_type, 0) <= 0:
                    continue
                total += 1
        return total

    def confirm_execution(self) -> bool:
        """Show execution confirmation and return explicit choice."""
        selected_types = self.get_selected_item_types()
        selected_chunk_keys = self.get_selected_chunk_keys()
        if not selected_types or not selected_chunk_keys:
            return False
        total_nodes = self._collect_target_count(selected_chunk_keys, selected_types)
        summary = build_confirmation_message(
            selected_chunk_keys=selected_chunk_keys,
            selected_types=selected_types,
            total_nodes=total_nodes,
        )
        answer = QMessageBox.question(
            self,
            "Confirm Remove Items",
            summary,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        return answer == QMessageBox.Yes

    def execute_remove(self) -> None:
        """Execute type-based deletion on selected chunks after confirmation."""
        selected_types = self.get_selected_item_types()
        selected_chunk_keys = self.get_selected_chunk_keys()
        if not selected_types or not selected_chunk_keys:
            return
        if not self.confirm_execution():
            return
        for chunk_key in selected_chunk_keys:
            chunk = self._get_chunk_by_key(chunk_key)
            if chunk is None:
                continue
            apply_type_deletion(chunk, selected_types)
        self._chunk_counts = {
            getattr(chunk, "key", index): get_chunk_type_counts(chunk)
            for index, chunk in enumerate(self._chunks)
        }
        self._visible_item_types = self._collect_visible_item_types()
        self._populate_item_types()
        self._populate_chunk_tree()
        self._refresh_preview()
        QMessageBox.information(
            self,
            "Remove Items",
            "Selected item types were removed in memory. Project is not auto-saved.",
        )


def create_batch_remove_items():
    """Create and execute the remove-items dialog."""
    app = QApplication.instance()
    parent = app.activeWindow() if app else None
    dialog = BatchRemoveItemsDialog(parent)
    dialog.exec_()
