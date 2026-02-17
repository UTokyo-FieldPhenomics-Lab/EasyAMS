import os
import csv
import re
import pyproj
from PySide2.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QLabel,
    QCheckBox,
    QTabWidget,
    QWidget,
    QListWidget,
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
    QComboBox,
    QSpinBox,
    QGroupBox,
    QFileDialog,
    QMessageBox,
    QSplitter,
    QHeaderView,
    QAbstractItemView,
    QGridLayout,
    QFrame,
    QFormLayout,
    QListWidgetItem,
)
from PySide2.QtCore import Qt
import Metashape

from ..utils import mprint


class BatchMarkerManager(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setModal(True)
        self.setWindowTitle("Batch Marker Manager")
        self.resize(1000, 700)

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # Main splitter to separate TreeView and Tabs
        self.splitter = QSplitter(Qt.Vertical)
        self.layout.addWidget(self.splitter)

        # Left Side: TreeView
        self.left_widget = QWidget()
        self.left_layout = QVBoxLayout()
        self.left_widget.setLayout(self.left_layout)

        # TreeView Controls
        self.tree_controls = QHBoxLayout()

        self.btn_check_all = QPushButton("Select All")
        self.btn_check_all.clicked.connect(self.select_all_chunks)
        self.btn_clear_all = QPushButton("Clear")
        self.btn_clear_all.clicked.connect(self.clear_all_chunks)

        self.btn_expand_all = QPushButton("Expand")
        self.btn_expand_all.clicked.connect(lambda: self.tree.expandAll())
        self.btn_collapse_all = QPushButton("Collapse")
        self.btn_collapse_all.clicked.connect(lambda: self.tree.collapseAll())

        self.tree_controls.addWidget(self.btn_check_all)
        self.tree_controls.addWidget(self.btn_clear_all)
        self.tree_controls.addWidget(self.btn_expand_all)
        self.tree_controls.addWidget(self.btn_collapse_all)
        self.tree_controls.addStretch()

        self.left_layout.addLayout(self.tree_controls)

        # TreeWidget
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(
            [
                "Markers",
                "X (m)",
                "Y (m)",
                "Z (m)",
                "Accuracy (m)",
                "Error (m)",
                "Projections",
            ]
        )
        self.tree.setColumnWidth(0, 200)
        self.tree.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.left_layout.addWidget(self.tree)

        self.splitter.addWidget(self.left_widget)

        # Right Side: Tabs
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)  # Metashape-like style
        self.splitter.addWidget(self.tabs)

        # Initialize Data
        self.refresh_tree_data()

        # Add Tabs
        self.init_tab1_ui()
        self.tabs.addTab(self.tab1, "Manage Markers")
        # Rename logic merged into tab1
        self.init_tab2_ui()
        self.tabs.addTab(self.tab2, "Import CSV")

        # Adjust splitter ratio
        self.splitter.setSizes([400, 600])

    def refresh_tree_data(self):
        """Scan all chunks and markers to populate the tree"""
        self.tree.clear()
        doc = Metashape.app.document

        for chunk in doc.chunks:
            chunk_item = QTreeWidgetItem(self.tree)
            chunk_item.setText(0, chunk.label)
            chunk_item.setFlags(chunk_item.flags() | Qt.ItemIsUserCheckable)
            chunk_item.setCheckState(0, Qt.Checked)
            chunk_item.setData(0, Qt.UserRole, chunk.key)  # Store chunk key

            for marker in chunk.markers:
                self.add_marker_node(chunk_item, marker, chunk.crs)

        self.tree.expandAll()

    def add_marker_node(self, parent, marker, crs):
        item = QTreeWidgetItem(parent)

        # Icon based on enabled status
        icon = "📍" if marker.enabled else "⛔"
        item.setText(0, f"{icon} {marker.label}")

        if marker.reference.location:
            loc = marker.reference.location
            item.setText(1, f"{loc.x:.4f}")
            item.setText(2, f"{loc.y:.4f}")
            item.setText(3, f"{loc.z:.4f}")

        if marker.reference.accuracy:
            acc = marker.reference.accuracy
            if isinstance(acc, Metashape.Vector):
                item.setText(4, f"{acc.x:.3f}")
            else:
                item.setText(4, f"{acc:.3f}")

        # Projections
        proj_count = len(marker.projections.keys())
        item.setText(6, str(proj_count))

        # Error (Need valid transform to estimate error, heavy calc, skipping for now or user provided?)
        # For Metashape, marker.reference.accuracy is the input accuracy.
        # marker.error methods exist but usually require processed data.
        # We leave Error column blank for now as requested "like Metashape UI" usually implies calculation.

    def select_all_chunks(self):
        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            root.child(i).setCheckState(0, Qt.Checked)

    def clear_all_chunks(self):
        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            root.child(i).setCheckState(0, Qt.Unchecked)

    def get_all_chunks(self):
        return Metashape.app.document.chunks

    # --- Tab 1: Manage & Rename Markers ---
    def init_tab1_ui(self):
        self.tab1 = QWidget()
        # Main Layout: Horizontal (List Left | Controls Right)
        layout = QHBoxLayout()
        self.tab1.setLayout(layout)

        # --- Left: List ---
        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("Unique Markers:"))
        self.marker_list = QListWidget()
        self.marker_list.setSelectionMode(QListWidget.ExtendedSelection)
        left_layout.addWidget(self.marker_list)
        layout.addLayout(left_layout, 1)

        # --- Right: Controls ---
        right_widget = QWidget()
        right_layout = QVBoxLayout()
        right_widget.setLayout(right_layout)

        # 1. Manage List Group
        gb_manage = QGroupBox("Manage List")
        gb_layout = QVBoxLayout()

        self.input_add_marker = QLineEdit()
        self.input_add_marker.setPlaceholderText("New Marker Name")
        gb_layout.addWidget(self.input_add_marker)

        hbox_add = QHBoxLayout()
        self.btn_add_marker = QPushButton("Add")
        self.btn_add_marker.clicked.connect(self.add_marker_to_list)
        self.btn_remove_marker = QPushButton("Remove Selected")
        self.btn_remove_marker.clicked.connect(self.remove_marker_from_list)

        hbox_add.addWidget(self.btn_add_marker)
        hbox_add.addWidget(self.btn_remove_marker)
        gb_layout.addLayout(hbox_add)

        gb_manage.setLayout(gb_layout)
        right_layout.addWidget(gb_manage)

        # 2. Rename Group
        gb_rename = QGroupBox("Batch Rename")
        rename_layout_box = QFormLayout()

        self.input_rename_from = QLineEdit()
        self.input_rename_to = QLineEdit()

        # Connect signals for real-time list update
        self.input_rename_from.textChanged.connect(self.update_list_preview)
        self.input_rename_to.textChanged.connect(self.update_list_preview)

        rename_layout_box.addRow("Find:", self.input_rename_from)
        rename_layout_box.addRow("Replace with:", self.input_rename_to)

        gb_rename.setLayout(rename_layout_box)
        right_layout.addWidget(gb_rename)

        right_layout.addStretch()

        # 3. Actions
        self.btn_preview_changes = QPushButton("Preview Changes")
        self.btn_preview_changes.clicked.connect(self.preview_changes_tab1)

        self.btn_reset_changes = QPushButton("Reset All")
        self.btn_reset_changes.clicked.connect(self.reset_tab1)

        self.btn_apply_changes = QPushButton("Apply All Changes")
        self.btn_apply_changes.clicked.connect(self.apply_changes_tab1)

        right_layout.addWidget(self.btn_preview_changes)
        right_layout.addWidget(self.btn_reset_changes)
        right_layout.addWidget(self.btn_apply_changes)

        layout.addWidget(right_widget, 1)

        self.populate_unique_markers()

    def update_list_preview(self):
        find_str = self.input_rename_from.text()
        replace_str = self.input_rename_to.text()

        for i in range(self.marker_list.count()):
            item = self.marker_list.item(i)
            # Use original from list or item text? item.text() is safe as setItemWidget doesn't change it.
            original = item.data(Qt.UserRole)
            if not original:
                # Fallback if UserRole empty (e.g. legacy items or added without data locally?)
                # If text is empty (due to previous preview), we are in trouble if we didn't store it.
                # But we always store it in populate and add.
                # Just in case text is present:
                if item.text():
                    original = item.text()
                    item.setData(Qt.UserRole, original)

            if not original:
                continue  # Should not happen

            if find_str and find_str in original:
                # Logic: "A<del>find</del><ins>replace</ins>B"
                replacement_html = f"<span style='color:red; text-decoration:line-through;'>{find_str}</span><span style='color:green;'>{replace_str}</span>"
                new_html = original.replace(find_str, replacement_html)

                label = QLabel(new_html)
                # Make background white or transparent?
                # Since we clear text, transparent is fine to show selection color?
                # But selection color might be behind.
                # Let's keep transparent but clear item text.
                label.setStyleSheet("background-color: transparent;")

                # IMPORTANT: Clear text to avoid double rendering (ghosting)
                item.setText("")
                self.marker_list.setItemWidget(item, label)
            else:
                # Restore
                if self.marker_list.itemWidget(item):
                    self.marker_list.removeItemWidget(item)
                item.setText(original)

    def populate_unique_markers(self):
        unique_names = set()
        for chunk in self.get_all_chunks():
            for marker in chunk.markers:
                unique_names.add(marker.label)

        self.marker_list.clear()
        self.original_unique_markers = sorted(list(unique_names))
        # Add items with UserRole data for future safety
        for name in self.original_unique_markers:
            item = QListWidgetItem(name)
            item.setData(Qt.UserRole, name)
            self.marker_list.addItem(item)

    def add_marker_to_list(self):
        name = self.input_add_marker.text().strip()
        if name and not self.marker_list.findItems(name, Qt.MatchExactly):
            item = QListWidgetItem(name)
            item.setData(Qt.UserRole, name)
            self.marker_list.addItem(item)
            self.input_add_marker.clear()

    def remove_marker_from_list(self):
        for item in self.marker_list.selectedItems():
            self.marker_list.takeItem(self.marker_list.row(item))

    def preview_changes_tab1(self):
        # 1. Calculate Expected States
        current_list_markers = set()
        for i in range(self.marker_list.count()):
            item = self.marker_list.item(i)
            # Prefer UserRole data as text might be just display or unchanged
            val = item.data(Qt.UserRole)
            if not val:
                val = item.text()
            current_list_markers.add(val)

        original_markers = set(self.original_unique_markers)

        # Deletions: In original but NOT in list
        to_delete = original_markers - current_list_markers

        # Additions: In list but NOT in original
        to_add = current_list_markers - original_markers

        # Renames: Valid original markers (not deleted) that match pattern
        find_str = self.input_rename_from.text()
        replace_str = self.input_rename_to.text()
        to_rename = {}  # old -> new

        if find_str:
            for m in original_markers:
                if m not in to_delete:
                    new_name = m.replace(find_str, replace_str)
                    if new_name != m:
                        to_rename[m] = new_name

        # 2. Update Tree Preview
        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            chunk_item = root.child(i)

            # Stats Counters
            count_add = 0
            count_del = 0
            count_ren = 0

            # Reset existing styles & clean names
            for j in range(chunk_item.childCount()):
                child = chunk_item.child(j)
                text = child.text(0)
                # Parse raw name
                raw_name = (
                    text.replace("📍 ", "")
                    .replace("⛔ ", "")
                    .replace("➕ ", "")
                    .split(" -> ")[0]
                    .strip()
                )

                # Check status
                if raw_name in to_delete:
                    child.setText(
                        0, f"⛔ {raw_name}"
                    )  # Keep icon consistent or use delete style? User said red strike
                    child.setForeground(0, Qt.red)
                    font = child.font(0)
                    font.setStrikeOut(True)
                    child.setFont(0, font)
                    count_del += 1
                elif raw_name in to_rename:
                    # Rename Preview style
                    new_name = to_rename[raw_name]
                    # Icon?
                    child.setText(0, f"📍 {raw_name} -> {new_name}")  # Assuming enabled
                    child.setForeground(0, Qt.blue)
                    font = child.font(0)
                    font.setStrikeOut(False)
                    child.setFont(0, font)
                    count_ren += 1
                else:
                    # Restore base
                    # We don't know enabled status here easily without looking up marker object again
                    # But we can assume blue square for simplicity or parse previous?
                    # Let's just use Blue square default as we are resetting.
                    # Or better: check if we can store marker ref in item? No, PySide crashes sometimes.
                    # Let's just leave it as is if it looks normal, or reset to standard.
                    if "⛔ " in text and raw_name not in to_delete:
                        child.setText(
                            0, f"⛔ {raw_name}"
                        )  # Restore disabled icon if it was there
                        child.setForeground(
                            0, Qt.gray
                        )  # Disabled style often gray? Or black.
                    else:
                        child.setText(0, f"📍 {raw_name}")
                        child.setForeground(0, Qt.black)
                    font = child.font(0)
                    font.setStrikeOut(False)
                    child.setFont(0, font)

            # Additions Preview
            current_child_names = set()
            for j in range(chunk_item.childCount()):
                raw = (
                    chunk_item.child(j)
                    .text(0)
                    .replace("📍 ", "")
                    .replace("⛔ ", "")
                    .replace("➕ ", "")
                    .split(" -> ")[0]
                    .strip()
                )
                current_child_names.add(raw)

            for new_marker in to_add:
                if new_marker not in current_child_names:
                    item = QTreeWidgetItem(chunk_item)
                    item.setText(0, f"➕ {new_marker}")
                    item.setForeground(0, Qt.green)
                    for col in range(1, 7):
                        item.setText(col, "-")
                    count_add += 1

            # Update Chunk Label with Stats
            base_label = chunk_item.text(0).split(" (")[0]
            stats_str = ""
            stats_parts = []
            if count_add > 0:
                stats_parts.append(f"+{count_add}")
            if count_del > 0:
                stats_parts.append(f"-{count_del}")
            if count_ren > 0:
                stats_parts.append(f"${count_ren}")

            if stats_parts:
                stats_str = f" ({', '.join(stats_parts)})"

            chunk_item.setText(0, f"{base_label}{stats_str}")

    def apply_changes_tab1(self):
        # Gather Rules
        current_list_markers = set()
        for i in range(self.marker_list.count()):
            item = self.marker_list.item(i)
            val = item.data(Qt.UserRole)
            if not val:
                val = item.text()
            if val:
                current_list_markers.add(val)
        original_markers = set(self.original_unique_markers)

        to_delete = original_markers - current_list_markers
        to_add = current_list_markers - original_markers

        find_str = self.input_rename_from.text()
        replace_str = self.input_rename_to.text()

        modified_chunks = 0
        root = self.tree.invisibleRootItem()

        for i in range(root.childCount()):
            chunk_item = root.child(i)
            if chunk_item.checkState(0) != Qt.Checked:
                continue

            chunk_key = chunk_item.data(0, Qt.UserRole)
            chunk = next(
                (c for c in Metashape.app.document.chunks if c.key == chunk_key), None
            )
            if not chunk:
                continue

            chunk_modified = False

            # 1. Deletions
            for marker in list(chunk.markers):
                if marker.label in to_delete:
                    chunk.remove(marker)
                    chunk_modified = True

            # 2. Renames (on remaining)
            if find_str:
                for marker in chunk.markers:
                    new_name = marker.label.replace(find_str, replace_str)
                    if new_name != marker.label:
                        marker.label = new_name
                        chunk_modified = True

            # 3. Additions
            for name in to_add:
                # Check exist (after rename!)
                existing = [m for m in chunk.markers if m.label == name]
                if not existing:
                    m = chunk.addMarker()
                    m.label = name
                    chunk_modified = True

            if chunk_modified:
                modified_chunks += 1

        self.refresh_tree_data()
        self.populate_unique_markers()
        self.input_rename_from.clear()
        self.input_rename_to.clear()
        QMessageBox.information(
            self, "Success", f"Applied changes to {modified_chunks} chunks."
        )

    def reset_tab1(self):
        self.input_add_marker.clear()
        self.input_rename_from.clear()
        self.input_rename_to.clear()
        # Reset list to original state
        self.marker_list.clear()
        self.marker_list.addItems(self.original_unique_markers)
        # Reset Treeview Preview
        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            chunk_item = root.child(i)
            # Reset existing styles
            for j in range(chunk_item.childCount()):
                child = chunk_item.child(j)
                text = child.text(0)
                # Parse raw name if modified
                if " -> " in text:
                    raw_name = text.split(" -> ")[0].replace("📍 ", "").strip()
                elif text.startswith("➕ "):
                    # This is a purely new node, we should ideally remove it or hide it?
                    # But wait, logic says "Add to list" adds "Add preview".
                    # Real remove is: we just re-populate tree data from Metashape!
                    # Actually, refresh_tree_data is cleaner.
                    pass
                else:
                    raw_name = text.replace("📍 ", "").strip()

        self.refresh_tree_data()  # Easiest way to clear visual artifacts
        QMessageBox.information(self, "Reset", "All pending changes cleared.")

    # --- Tab 2: Import Reference (formerly Tab 3) ---
    def init_tab2_ui(self):
        self.tab2 = QWidget()
        layout = QVBoxLayout()
        self.tab2.setLayout(layout)

        # 1. File Browse (Top)
        file_layout = QHBoxLayout()
        self.lbl_csv_path = QLabel("No file selected")
        self.lbl_csv_path.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        self.lbl_csv_path.setStyleSheet("background-color: white;")
        self.btn_browse_csv = QPushButton("...")
        self.btn_browse_csv.setFixedSize(30, 25)
        self.btn_browse_csv.clicked.connect(self.browse_csv_file)

        file_layout.addWidget(self.lbl_csv_path, 1)  # Label takes available space
        file_layout.addWidget(self.btn_browse_csv)
        layout.addLayout(file_layout)

        # 2. Coordinate System
        crs_group = QGroupBox("Coordinate System")
        crs_layout = QVBoxLayout()
        self.combo_crs = QComboBox()
        self.populate_crs_options()
        self.combo_crs.currentIndexChanged.connect(self.on_crs_changed)
        crs_layout.addWidget(self.combo_crs)
        crs_group.setLayout(crs_layout)
        layout.addWidget(crs_group)

        # 3. Columns Mapping
        col_group = QGroupBox("Columns")
        self.columns_layout = QGridLayout()

        # Row 0: Label
        self.columns_layout.addWidget(QLabel("Label:"), 0, 0)
        self.spin_col_label = QSpinBox()
        self.spin_col_label.setRange(1, 99)
        self.spin_col_label.valueChanged.connect(self.update_table_headers)
        self.columns_layout.addWidget(self.spin_col_label, 0, 1)

        self.chk_accuracy = QCheckBox("Accuracy")
        self.chk_accuracy.stateChanged.connect(self.toggle_accuracy_input)
        self.columns_layout.addWidget(self.chk_accuracy, 0, 2)

        # Row 1: X / Longitude
        self.lbl_col_x = QLabel("X (m):")
        self.columns_layout.addWidget(self.lbl_col_x, 1, 0)
        self.spin_col_x = QSpinBox()
        self.spin_col_x.setRange(1, 99)
        self.spin_col_x.setValue(2)
        self.spin_col_x.valueChanged.connect(self.update_table_headers)
        self.columns_layout.addWidget(self.spin_col_x, 1, 1)

        self.spin_prec_x = QSpinBox()
        self.spin_prec_x.setRange(0, 15)
        self.spin_prec_x.setValue(8)  # Default precision
        self.spin_prec_x.setToolTip("Decimal places")
        self.spin_prec_x.setEnabled(False)
        self.spin_prec_x.valueChanged.connect(lambda: self.load_csv_preview())
        self.columns_layout.addWidget(self.spin_prec_x, 1, 2)

        # Row 2: Y / Latitude
        self.lbl_col_y = QLabel("Y (m):")
        self.columns_layout.addWidget(self.lbl_col_y, 2, 0)
        self.spin_col_y = QSpinBox()
        self.spin_col_y.setRange(1, 99)
        self.spin_col_y.setValue(3)
        self.spin_col_y.valueChanged.connect(self.update_table_headers)
        self.columns_layout.addWidget(self.spin_col_y, 2, 1)

        self.spin_prec_y = QSpinBox()
        self.spin_prec_y.setRange(0, 15)
        self.spin_prec_y.setValue(8)
        self.spin_prec_y.setEnabled(False)
        self.spin_prec_y.valueChanged.connect(lambda: self.load_csv_preview())
        self.columns_layout.addWidget(self.spin_prec_y, 2, 2)

        # Row 3: Z / Altitude
        self.lbl_col_z = QLabel("Z (m):")
        self.columns_layout.addWidget(self.lbl_col_z, 3, 0)
        self.spin_col_z = QSpinBox()
        self.spin_col_z.setRange(1, 99)
        self.spin_col_z.setValue(4)
        self.spin_col_z.valueChanged.connect(self.update_table_headers)
        self.columns_layout.addWidget(self.spin_col_z, 3, 1)

        self.spin_prec_z = QSpinBox()
        self.spin_prec_z.setRange(0, 15)
        self.spin_prec_z.setValue(8)
        self.spin_prec_z.setEnabled(False)
        self.spin_prec_z.valueChanged.connect(lambda: self.load_csv_preview())
        self.columns_layout.addWidget(self.spin_prec_z, 3, 2)

        # Row 4: Accuracy Column (Removed)

        # Row 5: Start Row - Move to separate bottom area or keep in grid?
        # User Fig 1 doesn't show Start Row. But we need it.
        # Let's put it at the bottom.

        col_group.setLayout(self.columns_layout)
        layout.addWidget(col_group)

        # Start Row separate
        row_layout = QHBoxLayout()
        row_layout.addWidget(QLabel("Start Row:"))
        self.spin_start_row = QSpinBox()
        self.spin_start_row.setValue(1)
        self.spin_start_row.setMinimum(1)
        self.spin_start_row.valueChanged.connect(
            self.update_table_headers
        )  # Might affect data but not headers mapping.
        # But reloading preview might be needed.
        # Check if we should block signals or just let it update
        self.spin_start_row.valueChanged.connect(
            lambda: self.load_csv_preview()
            if self.lbl_csv_path.text() != "No file selected"
            else None
        )
        row_layout.addWidget(self.spin_start_row)
        row_layout.addStretch()
        layout.addLayout(row_layout)

        # 4. Preview Table
        layout.addWidget(QLabel("First 20 lines preview:"))
        self.table_preview = QTableWidget()
        self.table_preview.setRowCount(0)
        self.table_preview.setColumnCount(0)
        self.table_preview.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_preview.verticalHeader().setVisible(True)  # Show row numbers
        layout.addWidget(self.table_preview)

        # Actions
        action_layout = QHBoxLayout()
        self.btn_import_reset = QPushButton("Reset")
        self.btn_import_reset.clicked.connect(self.reset_tab2)

        self.btn_preview_changes = QPushButton("Preview Changes")
        self.btn_preview_changes.setToolTip(
            "Show changes in tree view (Green=New, Red=Old)"
        )
        self.btn_preview_changes.clicked.connect(self.preview_changes_tab2)

        self.btn_import_apply = QPushButton("Import Reference")
        self.btn_import_apply.clicked.connect(self.apply_import_reference)

        action_layout.addWidget(self.btn_import_reset)
        action_layout.addWidget(self.btn_preview_changes)
        action_layout.addWidget(self.btn_import_apply)
        layout.addLayout(action_layout)

    def toggle_accuracy_input(self, state):
        enabled = state == Qt.Checked
        self.spin_prec_x.setEnabled(enabled)
        self.spin_prec_y.setEnabled(enabled)
        self.spin_prec_z.setEnabled(enabled)
        self.load_csv_preview()  # Refresh preview logic

    def update_table_headers(self):
        # Update dynamic headers based on spinbox values
        cols = self.table_preview.columnCount()
        if cols == 0:
            return

        # Default headers
        headers = [str(i + 1) for i in range(cols)]

        # Map indices to names
        # Spinboxes are 1-based, list is 0-based
        mapping = {
            self.spin_col_label.value() - 1: "Label",
            self.spin_col_x.value() - 1: self.lbl_col_x.text().replace(":", ""),
            self.spin_col_y.value() - 1: self.lbl_col_y.text().replace(":", ""),
            self.spin_col_z.value() - 1: self.lbl_col_z.text().replace(":", ""),
        }

        for idx, name in mapping.items():
            if 0 <= idx < cols:
                headers[idx] = name

        self.table_preview.setHorizontalHeaderLabels(headers)

    def populate_crs_options(self):
        self.combo_crs.clear()

        # We will store items in a list first to check for duplicates
        # Item format: (Label, Data)
        items = []

        # 1. Local
        items.append(
            (
                "Local Coordinates (m)",
                Metashape.CoordinateSystem(
                    'LOCAL_CS["Local Coordinates (m)",LOCAL_DATUM["Local Datum",0],UNIT["metre",1,AUTHORITY["EPSG","9001"]]]'
                ),
            )
        )

        # 2. WGS 84
        items.append(("WGS 84 (EPSG::4326)", Metashape.CoordinateSystem("EPSG::4326")))

        # 3. Other chunks CRSs
        seen_crs_names = set([crs.name for _, crs in items])

        for chunk in Metashape.app.document.chunks:
            if chunk.crs.name not in seen_crs_names:
                items.append((chunk.crs.name, chunk.crs))
                seen_crs_names.add(chunk.crs.name)

        # 4. Add items to Combo
        self.combo_crs.blockSignals(True)
        for label, data in items:
            self.combo_crs.addItem(label, data)
        self.combo_crs.blockSignals(False)

        # 5. Handle Active Chunk Selection
        # If active chunk has CRS, try to find it in the list.
        # if active_chunk and active_chunk.crs:
        #     active_wkt = active_chunk.crs.wkt
        #     found_index = -1

        #     for i in range(self.combo_crs.count()):
        #         item_data = self.combo_crs.itemData(i)
        #         # Check match
        #         if item_data is None: continue # Skip Local

        #         if isinstance(item_data, Metashape.CoordinateSystem):
        #             if item_data.wkt == active_wkt:
        #                 found_index = i
        #                 break

        #     self.combo_crs.blockSignals(True)
        #     if found_index >= 0:
        #         self.combo_crs.setCurrentIndex(found_index)
        #     else:
        #         # Add as Active
        #         self.combo_crs.insertItem(0, f"Active: {active_chunk.crs.name}", active_chunk.crs)
        #         self.combo_crs.setCurrentIndex(0)
        #     self.combo_crs.blockSignals(False)
        # else:
        #     # Active chunk is Local (None)
        #     idx = self.combo_crs.findText("Local Coordinates (m)")
        #     self.combo_crs.blockSignals(True)
        #     if idx >= 0: self.combo_crs.setCurrentIndex(idx)
        #     self.combo_crs.blockSignals(False)

        # 6. More...
        self.combo_crs.addItem("More...", "MORE")

    def on_crs_changed(self, index):
        data = self.combo_crs.itemData(index)
        if data == "MORE":
            crs = Metashape.app.getCoordinateSystem()
            if crs:
                # Add and select
                self.combo_crs.blockSignals(True)
                self.combo_crs.insertItem(self.combo_crs.count() - 1, crs.name, crs)
                self.combo_crs.setCurrentIndex(self.combo_crs.count() - 2)
                self.combo_crs.blockSignals(False)
                data = crs
            else:
                # Revert to previous valid? Or just select index 0?
                self.combo_crs.blockSignals(True)
                self.combo_crs.setCurrentIndex(0)
                self.combo_crs.blockSignals(False)
                return

        # Update labels by parsing CRS
        labels = ["X (m):", "Y (m):", "Z (m):"]  # Default

        unit_dict = {"degree": "°", "metre": "m"}

        if (
            isinstance(data, Metashape.CoordinateSystem)
            and data.name != "Local Coordinates (m)"
        ):
            mprint(f"[Tab2]:CRS: selected to {data}")
            success = False
            # Try PyProj first (Generic & Robust)
            try:
                crs_obj = pyproj.CRS(data.wkt)
                axes = crs_obj.axis_info
                mprint(f"[Tab2]:CRS: crs_obj={crs_obj}\n        axes={axes}\n")

                if axes and len(axes) >= 2:
                    labels[0] = (
                        f"{axes[0].name if len(axes[0].name) < 10 else axes[0].abbrev} "
                        f"({unit_dict.get(axes[0].unit_name, axes[0].unit_name)}):"
                    )
                    labels[1] = (
                        f"{axes[1].name if len(axes[1].name) < 10 else axes[1].abbrev} "
                        f"({unit_dict.get(axes[1].unit_name, axes[1].unit_name)}):"
                    )
                    if len(axes) > 2:
                        labels[2] = (
                            f"{axes[2].name if len(axes[2].name) < 10 else axes[2].abbrev} "
                            f"({unit_dict.get(axes[2].unit_name, axes[2].unit_name)}):"
                        )
                    else:
                        labels[2] = (
                            "Altitude (m):"  # Default for Z if missing in 2D CRS
                        )
                    success = True
                    mprint(f"[Tab2]:CRS: parsed labels -> {labels}")
            except Exception as e:
                mprint(f"[Tab2]:CRS: PyProj failed: {e}")
                pass

            if not success:
                mprint(
                    f"[Tab2]:CRS: Parse {data} wkt: {data.wkt} wk2: {data.wkt2} failed, try string re parse"
                )
                # Fallback: Regex on WKT
                wkt = data.wkt
                matches = re.findall(r'AXIS\["([^"]+)"', wkt)
                if matches:
                    if len(matches) >= 1:
                        labels[0] = matches[0] + ":"
                    if len(matches) >= 2:
                        labels[1] = matches[1] + ":"
                    if len(matches) >= 3:
                        labels[2] = matches[2] + ":"
                elif data.geogcs:
                    labels[0] = "Longitude:"
                    labels[1] = "Latitude:"
                    labels[2] = "Altitude:"
                else:
                    labels[0] = "X (m):"
                    labels[1] = "Y (m):"
                    labels[2] = "Z (m):"

        self.lbl_col_x.setText(labels[0])
        self.lbl_col_y.setText(labels[1])
        self.lbl_col_z.setText(labels[2])

        self.update_table_headers()

    def browse_csv_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open CSV", "", "CSV Files (*.csv *.txt)"
        )
        if path:
            self.lbl_csv_path.setText(path)
            self.load_csv_preview(path)

    def load_csv_preview(self, path=None):
        if not path:
            path = self.lbl_csv_path.text()
            if not os.path.exists(path):
                return

        try:
            with open(path, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                rows = []
                # Skip rows logic?
                # Start Row in UI is 1-based index of DATA start.
                # But preview usually shows file content raw.
                # Let's show first 20 lines RAW.
                for _ in range(20):
                    try:
                        row = next(reader)
                        rows.append(row)
                    except StopIteration:
                        break

            if not rows:
                return

            # Setup table
            max_cols = max(len(r) for r in rows)
            self.table_preview.setColumnCount(max_cols)
            self.table_preview.setRowCount(len(rows))

            # Get settings for live preview
            idx_x = self.spin_col_x.value() - 1
            idx_y = self.spin_col_y.value() - 1
            idx_z = self.spin_col_z.value() - 1

            show_prec = self.chk_accuracy.isChecked()
            prec_x = self.spin_prec_x.value()
            prec_y = self.spin_prec_y.value()
            prec_z = self.spin_prec_z.value()

            for r_idx, row in enumerate(rows):
                for c_idx, val in enumerate(row):
                    display_val = val
                    if show_prec:
                        try:
                            if c_idx == idx_x:
                                display_val = f"{float(val):.{prec_x}f}"
                            elif c_idx == idx_y:
                                display_val = f"{float(val):.{prec_y}f}"
                            elif c_idx == idx_z:
                                display_val = f"{float(val):.{prec_z}f}"
                        except ValueError:
                            pass

                    self.table_preview.setItem(
                        r_idx, c_idx, QTableWidgetItem(display_val)
                    )

            self.update_table_headers()

        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to read CSV: {e}")

    def reset_tab2(self):
        self.spin_col_label.setValue(1)
        self.spin_col_x.setValue(2)
        self.spin_col_y.setValue(3)
        self.spin_col_z.setValue(4)
        self.spin_prec_x.setValue(8)
        self.spin_prec_y.setValue(8)
        self.spin_prec_z.setValue(8)
        self.chk_accuracy.setChecked(False)  # Should trigger toggle to disable
        self.spin_start_row.setValue(1)
        self.lbl_csv_path.setText("No file selected")
        self.table_preview.clear()
        self.table_preview.setRowCount(0)
        self.table_preview.setColumnCount(0)
        # Helper: Reset Combo?
        self.combo_crs.setCurrentIndex(0)
        self.refresh_tree_data()

    def preview_changes_tab2(self):
        marker_data = self.parse_csv_for_reference()
        if not marker_data:
            return

        root = self.tree.invisibleRootItem()
        modified_count = 0

        # We need to know decimal precision for display
        use_prec = self.chk_accuracy.isChecked()
        prec_x = self.spin_prec_x.value()
        prec_y = self.spin_prec_y.value()
        prec_z = self.spin_prec_z.value()

        def fmt_val(v, prec):
            if v is None:
                return "None"
            if use_prec:
                return f"{v:.{prec}f}"
            else:
                return f"{v}"

        for i in range(root.childCount()):
            chunk_item = root.child(i)
            if chunk_item.checkState(0) != Qt.Checked:
                continue

            chunk_key = chunk_item.data(0, Qt.UserRole)
            chunk = next(
                (c for c in Metashape.app.document.chunks if c.key == chunk_key), None
            )
            if not chunk:
                continue

            updates = 0
            for j in range(chunk_item.childCount()):
                m_item = chunk_item.child(j)
                m_label = m_item.data(0, Qt.UserRole)
                if not m_label:
                    m_label = m_item.text(0).split(" ", 1)[-1]

                if m_label in marker_data:
                    new_loc, _ = marker_data[m_label]

                    marker = next(
                        (m for m in chunk.markers if m.label == m_label), None
                    )
                    current_loc = None
                    if marker and marker.reference.location:
                        current_loc = marker.reference.location

                    # Updates for X (col 1), Y (col 2), Z (col 3)
                    # Helper for col render
                    def render_col(col_idx, curr, new, prec):
                        html = ""
                        s_new = fmt_val(new, prec)
                        if curr is None:
                            html = f'<font color="green"><b>{s_new}</b></font>'
                        else:
                            s_curr = fmt_val(curr, prec)
                            if s_curr != s_new:  # Diff string representation
                                html = f'<font color="red"><s>{s_curr}</s></font> <font color="green"><b>{s_new}</b></font>'
                            else:
                                html = s_curr  # No change visually

                        lbl = QLabel(html)
                        lbl.setTextFormat(Qt.RichText)
                        # Clear text to avoid overlap
                        m_item.setText(col_idx, "")
                        self.tree.setItemWidget(m_item, col_idx, lbl)

                    render_col(
                        1, current_loc.x if current_loc else None, new_loc.x, prec_x
                    )
                    render_col(
                        2, current_loc.y if current_loc else None, new_loc.y, prec_y
                    )
                    render_col(
                        3, current_loc.z if current_loc else None, new_loc.z, prec_z
                    )

                    updates += 1

            if updates > 0:
                modified_count += 1
                chunk_item.setText(
                    0, chunk_item.text(0).split(" (", 1)[0] + f" ({updates} refs)"
                )

        if modified_count == 0:
            QMessageBox.information(
                self, "Preview", "No markers matched in selected chunks."
            )

    def apply_import_reference(self):
        csv_path = self.lbl_csv_path.text()
        if not os.path.exists(csv_path):
            QMessageBox.warning(self, "Error", "Please select a valid CSV file.")
            return

    def parse_csv_for_reference(self):
        """Parses CSV based on current tab 2 settings. Returns dict {label: (Vector_loc, Vector_acc or None)}"""
        csv_path = self.lbl_csv_path.text()
        if not os.path.exists(csv_path):
            QMessageBox.warning(self, "Error", "Please select a valid CSV file.")
            return {}

        # Get mapping (0-based)
        idx_label = self.spin_col_label.value() - 1
        idx_x = self.spin_col_x.value() - 1
        idx_y = self.spin_col_y.value() - 1
        idx_z = self.spin_col_z.value() - 1

        use_manual_acc = self.chk_accuracy.isChecked()
        prec_x = self.spin_prec_x.value()
        prec_y = self.spin_prec_y.value()
        prec_z = self.spin_prec_z.value()

        start_row = self.spin_start_row.value()  # 1-based

        marker_data = {}  # label -> (Vector, accuracy)

        try:
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                for i, row in enumerate(reader):
                    if i + 1 < start_row:
                        continue

                    try:
                        label = row[idx_label].strip()
                        x_raw = float(row[idx_x])
                        y_raw = float(row[idx_y])
                        z_raw = float(row[idx_z])

                        acc = None
                        if use_manual_acc:
                            # Round Coords
                            x = round(x_raw, prec_x)
                            y = round(y_raw, prec_y)
                            z = round(z_raw, prec_z)
                            # Set accuracy
                            acc = Metashape.Vector(
                                [pow(10, -prec_x), pow(10, -prec_y), pow(10, -prec_z)]
                            )
                        else:
                            x, y, z = x_raw, y_raw, z_raw

                        marker_data[label] = (Metashape.Vector([x, y, z]), acc)
                    except (IndexError, ValueError) as e:
                        pass
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to process CSV: {e}")
            return {}

        return marker_data

    def apply_import_reference(self):
        marker_data = self.parse_csv_for_reference()
        if not marker_data:
            return

        target_crs = self.combo_crs.currentData()
        if target_crs == "MORE":
            return

        # Apply to selected chunks
        root = self.tree.invisibleRootItem()
        modified_chunks = 0

        for i in range(root.childCount()):
            chunk_item = root.child(i)
            if chunk_item.checkState(0) != Qt.Checked:
                continue

            chunk_key = chunk_item.data(0, Qt.UserRole)
            chunk = next(
                (c for c in Metashape.app.document.chunks if c.key == chunk_key), None
            )
            if not chunk:
                continue

            # 1. Update CRS
            if target_crs:
                chunk.crs = target_crs

            # 2. Update Markers
            count = 0
            for marker in chunk.markers:
                if marker.label in marker_data:
                    coords, accuracy = marker_data[marker.label]
                    marker.reference.location = coords
                    if accuracy is not None:
                        marker.reference.accuracy = accuracy
                    marker.reference.enabled = True
                    count += 1

            if count > 0:
                modified_chunks += 1

        QMessageBox.information(
            self,
            "Success",
            f"Imported reference for {len(marker_data)} markers in {modified_chunks} chunks.",
        )
        self.refresh_tree_data()


def create_batch_marker_manager():
    app = Metashape.app
    from PySide2.QtWidgets import QApplication

    parent = QApplication.activeWindow()
    dlg = BatchMarkerManager(parent)
    dlg.exec_()
