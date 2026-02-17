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
        actions.addStretch()
        actions.addWidget(cancel_btn)
        actions.addWidget(execute_btn)
        layout.addLayout(actions)
        self.setLayout(layout)

    def _populate_item_types(self) -> None:
        """Fill item list and disable unsupported item types."""
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


def create_batch_remove_items():
    """Create and execute the remove-items dialog."""
    app = QApplication.instance()
    parent = app.activeWindow() if app else None
    dialog = BatchRemoveItemsDialog(parent)
    dialog.exec_()
