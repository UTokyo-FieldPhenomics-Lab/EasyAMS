import os
import csv
from PySide2.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                              QTreeWidget, QTreeWidgetItem, QLabel, QCheckBox, 
                              QTabWidget, QWidget, QListWidget, QLineEdit, 
                              QTableWidget, QTableWidgetItem, QComboBox, 
                              QSpinBox, QGroupBox, QFileDialog, QMessageBox, QSplitter,
                              QHeaderView, QAbstractItemView, QGridLayout, QFrame, QFormLayout, 
                              QListWidgetItem)
from PySide2.QtCore import Qt
import Metashape

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
        self.tree.setHeaderLabels(["Markers", "X (m)", "Y (m)", "Z (m)", "Accuracy (m)", "Error (m)", "Projections"])
        self.tree.setColumnWidth(0, 200)
        self.tree.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.left_layout.addWidget(self.tree)

        self.splitter.addWidget(self.left_widget)

        # Right Side: Tabs
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True) # Metashape-like style
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
            chunk_item.setData(0, Qt.UserRole, chunk.key) # Store chunk key

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
            
            if not original: continue # Should not happen

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
            if not val: val = item.text()
            current_list_markers.add(val)
            
        original_markers = set(self.original_unique_markers)
        
        # Deletions: In original but NOT in list
        to_delete = original_markers - current_list_markers
        
        # Additions: In list but NOT in original
        to_add = current_list_markers - original_markers
        
        # Renames: Valid original markers (not deleted) that match pattern
        find_str = self.input_rename_from.text()
        replace_str = self.input_rename_to.text()
        to_rename = {} # old -> new
        
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
                raw_name = text.replace("📍 ", "").replace("⛔ ", "").replace("➕ ", "").split(" -> ")[0].strip()
                
                # Check status
                if raw_name in to_delete:
                    child.setText(0, f"⛔ {raw_name}") # Keep icon consistent or use delete style? User said red strike
                    child.setForeground(0, Qt.red)
                    font = child.font(0); font.setStrikeOut(True); child.setFont(0, font)
                    count_del += 1
                elif raw_name in to_rename:
                    # Rename Preview style
                    new_name = to_rename[raw_name]
                    # Icon?
                    child.setText(0, f"📍 {raw_name} -> {new_name}") # Assuming enabled
                    child.setForeground(0, Qt.blue)
                    font = child.font(0); font.setStrikeOut(False); child.setFont(0, font)
                    count_ren += 1
                else:
                    # Restore base
                    # We don't know enabled status here easily without looking up marker object again
                    # But we can assume blue square for simplicity or parse previous?
                    # Let's just use Blue square default as we are resetting.
                    # Or better: check if we can store marker ref in item? No, PySide crashes sometimes.
                    # Let's just leave it as is if it looks normal, or reset to standard.
                    if "⛔ " in text and raw_name not in to_delete:
                         child.setText(0, f"⛔ {raw_name}") # Restore disabled icon if it was there
                         child.setForeground(0, Qt.gray) # Disabled style often gray? Or black.
                    else:
                         child.setText(0, f"📍 {raw_name}")
                         child.setForeground(0, Qt.black)
                    font = child.font(0); font.setStrikeOut(False); child.setFont(0, font)

            # Additions Preview
            current_child_names = set()
            for j in range(chunk_item.childCount()):
                raw = chunk_item.child(j).text(0).replace("📍 ", "").replace("⛔ ", "").replace("➕ ", "").split(" -> ")[0].strip()
                current_child_names.add(raw)
                
            for new_marker in to_add:
                 if new_marker not in current_child_names:
                     item = QTreeWidgetItem(chunk_item)
                     item.setText(0, f"➕ {new_marker}")
                     item.setForeground(0, Qt.green)
                     for col in range(1, 7): item.setText(col, "-")
                     count_add += 1
            
            # Update Chunk Label with Stats
            base_label = chunk_item.text(0).split(" (")[0]
            stats_str = ""
            stats_parts = []
            if count_add > 0: stats_parts.append(f"+{count_add}")
            if count_del > 0: stats_parts.append(f"-{count_del}")
            if count_ren > 0: stats_parts.append(f"${count_ren}")
            
            if stats_parts:
                stats_str = f" ({', '.join(stats_parts)})"
            
            chunk_item.setText(0, f"{base_label}{stats_str}")

    def apply_changes_tab1(self):
        # Gather Rules
        # Gather Rules
        current_list_markers = set()
        for i in range(self.marker_list.count()):
            item = self.marker_list.item(i)
            val = item.data(Qt.UserRole)
            if not val: val = item.text()
            if val: current_list_markers.add(val)
        original_markers = set(self.original_unique_markers)
        
        to_delete = original_markers - current_list_markers
        to_add = current_list_markers - original_markers
        
        find_str = self.input_rename_from.text()
        replace_str = self.input_rename_to.text()
        
        modified_chunks = 0
        root = self.tree.invisibleRootItem()
        
        for i in range(root.childCount()):
            chunk_item = root.child(i)
            if chunk_item.checkState(0) != Qt.Checked: continue
            
            chunk_key = chunk_item.data(0, Qt.UserRole)
            chunk = next((c for c in Metashape.app.document.chunks if c.key == chunk_key), None)
            if not chunk: continue
            
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
        QMessageBox.information(self, "Success", f"Applied changes to {modified_chunks} chunks.")

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
        
        self.refresh_tree_data() # Easiest way to clear visual artifacts
        QMessageBox.information(self, "Reset", "All pending changes cleared.")

    # --- Tab 3: Import Reference ---
    def init_tab2_ui(self):
        self.tab2 = QWidget()
        layout = QVBoxLayout()
        self.tab2.setLayout(layout)
        
        # 1. Coordinate System
        crs_group = QGroupBox("Coordinate System")
        crs_layout = QVBoxLayout()
        
        self.combo_crs = QComboBox()
        self.combo_crs.currentIndexChanged.connect(self.on_crs_changed)
        crs_layout.addWidget(self.combo_crs)
        
        crs_group.setLayout(crs_layout)
        layout.addWidget(crs_group)
        
        # 2. File Selection
        file_layout = QHBoxLayout()
        self.label_csv_path = QLabel("No file selected")
        btn_browse_csv = QPushButton("Browse CSV...")
        btn_browse_csv.clicked.connect(self.browse_csv_file)
        
        file_layout.addWidget(btn_browse_csv)
        file_layout.addWidget(self.label_csv_path)
        layout.addLayout(file_layout)
        
        # 3. Columns Mapping
        columns_group = QGroupBox("Columns")
        columns_layout = QGridLayout()
        
        # Headers/SpinBoxes
        self.spin_col_label = QSpinBox()
        self.spin_col_x = QSpinBox()
        self.spin_col_y = QSpinBox()
        self.spin_col_z = QSpinBox()
        self.spin_col_acc = QSpinBox()
        
        # Defaults
        self.spin_col_label.setValue(1)
        self.spin_col_x.setValue(2)
        self.spin_col_y.setValue(3)
        self.spin_col_z.setValue(4)
        self.spin_col_acc.setValue(5)
        
        # Labels (Dynamic)
        self.label_x_title = QLabel("X/Long:")
        self.label_y_title = QLabel("Y/Lat:")
        self.label_z_title = QLabel("Z/Alt:")
        
        columns_layout.addWidget(QLabel("Label:"), 0, 0)
        columns_layout.addWidget(self.spin_col_label, 0, 1)
        
        self.cb_acc = QCheckBox("Accuracy")
        columns_layout.addWidget(self.cb_acc, 0, 2)
        columns_layout.addWidget(self.spin_col_acc, 0, 3)
        
        columns_layout.addWidget(self.label_x_title, 1, 0)
        columns_layout.addWidget(self.spin_col_x, 1, 1)
        
        columns_layout.addWidget(self.label_y_title, 1, 2)
        columns_layout.addWidget(self.spin_col_y, 1, 3)
        
        columns_layout.addWidget(self.label_z_title, 1, 4)
        columns_layout.addWidget(self.spin_col_z, 1, 5)
        
        # Start Row
        columns_layout.addWidget(QLabel("Start Row:"), 2, 0)
        self.spin_start_row = QSpinBox()
        self.spin_start_row.setValue(2) # Default skip header
        self.spin_start_row.setMinimum(1)
        columns_layout.addWidget(self.spin_start_row, 2, 1)
        
        columns_group.setLayout(columns_layout)
        layout.addWidget(columns_group)

        # 4. Preview Table
        layout.addWidget(QLabel("First 20 lines preview:"))
        self.table_preview = QTableWidget()
        self.table_preview.setColumnCount(5) # Init default
        layout.addWidget(self.table_preview)
        
        layout.addWidget(self.table_preview)
        
        # Actions
        action_layout = QHBoxLayout()
        self.btn_import_reset = QPushButton("Reset")
        self.btn_import_reset.clicked.connect(self.reset_tab2)
        self.btn_import_apply = QPushButton("Import Reference")
        self.btn_import_apply.clicked.connect(self.apply_import_reference)
        
        action_layout.addWidget(self.btn_import_reset)
        action_layout.addWidget(self.btn_import_apply)
        layout.addLayout(action_layout)
        
        # Connect signals for preview update
        self.spin_start_row.valueChanged.connect(self.update_csv_preview_highlight)
        self.spin_col_label.valueChanged.connect(self.update_csv_preview_highlight)
        self.spin_col_x.valueChanged.connect(self.update_csv_preview_highlight)
        self.spin_col_y.valueChanged.connect(self.update_csv_preview_highlight)
        self.spin_col_z.valueChanged.connect(self.update_csv_preview_highlight)

        # Init CRS options
        self.populate_crs_options()

    def populate_crs_options(self):
        self.combo_crs.clear()
        
        # 1. Current Active Chunk CRS (Default)
        doc = Metashape.app.document
        if doc.chunk and doc.chunk.crs:
            self.add_crs_to_combo(doc.chunk.crs, "Active Chunk")
        
        # 2. Presets
        self.combo_crs.addItem("Local Coordinates (m)", "Local")
        self.combo_crs.addItem("WGS 84 (EPSG::4326)", "EPSG::4326")
        
        # 3. All Chunks CRS
        seen_crs = set()
        if doc.chunk and doc.chunk.crs: seen_crs.add(str(doc.chunk.crs))
        
        for chunk in doc.chunks:
            if chunk.crs and str(chunk.crs) not in seen_crs:
                self.add_crs_to_combo(chunk.crs, f"Chunk: {chunk.label}")
                seen_crs.add(str(chunk.crs))
                
        # 4. More...
        self.combo_crs.addItem("More...", "MORE")

    def add_crs_to_combo(self, crs, label_prefix=""):
        # Helper to format decent label
        auth = crs.authority
        name = crs.name
        full_label = f"{name}"
        if auth: full_label += f" ({auth})"
        if label_prefix: full_label = f"[{label_prefix}] {full_label}"
        
        self.combo_crs.addItem(full_label, crs) # Store crs object as user data

    def on_crs_changed(self, index):
        data = self.combo_crs.itemData(index)
        
        if data == "MORE":
             # Open Metashape dialog
             new_crs = Metashape.app.getCoordinateSystem("Select Coordinate System")
             if new_crs:
                 self.add_crs_to_combo(new_crs, "User Selected")
                 self.combo_crs.setCurrentIndex(self.combo_crs.count() - 1)
                 data = new_crs
             else:
                 # Revert to valid? or stay? 
                 pass
        
        # Update Labels
        if isinstance(data, Metashape.CoordinateSystem):
            # Check if geographic (no direct isGeographic prop in simple API, check proj4 or geogcs)
             is_geo = "long" in data.wkt.lower() or "lat" in data.wkt.lower()
             if is_geo:
                 self.label_x_title.setText("Longitude:")
                 self.label_y_title.setText("Latitude:")
                 self.label_z_title.setText("Altitude:")
             else:
                 self.label_x_title.setText("Easting (X):")
                 self.label_y_title.setText("Northing (Y):")
                 self.label_z_title.setText("Altitude (Z):")
        elif data == "Local":
             self.label_x_title.setText("X (m):")
             self.label_y_title.setText("Y (m):")
             self.label_z_title.setText("Z (m):")
        elif data == "EPSG::4326":
             self.label_x_title.setText("Longitude:")
             self.label_y_title.setText("Latitude:")
             self.label_z_title.setText("Altitude:")
    
    def browse_csv_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select CSV", "", "CSV Files (*.csv);;All Files (*)")
        if path:
            self.csv_path = path
            self.label_csv_path.setText(os.path.basename(path))
            self.load_csv_preview()

    def load_csv_preview(self):
        if not hasattr(self, 'csv_path'): return
        
        try:
            with open(self.csv_path, 'r', encoding='utf-8') as f:
                # Read first 20 lines
                lines = [line.strip() for line in f if line.strip()]
                preview_lines = lines[:20]
                
            if not preview_lines: return
            
            # Detect cols from first line logic (comma)
            cols_count = len(preview_lines[0].split(','))
            self.table_preview.setColumnCount(cols_count)
            self.table_preview.setRowCount(len(preview_lines))
            
            for r, line in enumerate(preview_lines):
                parts = line.split(',')
                for c, text in enumerate(parts):
                    if c < cols_count:
                        self.table_preview.setItem(r, c, QTableWidgetItem(text))
            
            self.update_csv_preview_highlight()
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to read CSV: {e}")

    def reset_tab2(self):
        self.spin_col_label.setValue(1)
        self.spin_col_x.setValue(2)
        self.spin_col_y.setValue(3)
        self.spin_col_z.setValue(4)
        self.spin_col_acc.setValue(5)
        self.cb_acc.setChecked(False)
        self.spin_start_row.setValue(2)
        self.combo_crs.setCurrentIndex(0) # Default to first (Active Chunk)
        self.label_csv_path.setText("No file selected")
        if hasattr(self, 'csv_path'): del self.csv_path
        self.table_preview.clearContents()
        self.table_preview.setRowCount(0)

    def update_csv_preview_highlight(self):
        # Todo: Highlight columns used for X, Y, Z, Label background color
        # This is purely visual
        pass

    def apply_import_reference(self):
        if not hasattr(self, 'csv_path'): 
            QMessageBox.warning(self, "Error", "Please select a CSV file first.")
            return

        # Get Selected CRS
        idx = self.combo_crs.currentIndex()
        crs_data = self.combo_crs.itemData(idx)
        
        target_crs = None
        if isinstance(crs_data, Metashape.CoordinateSystem):
            target_crs = crs_data
        elif crs_data == "EPSG::4326":
            target_crs = Metashape.CoordinateSystem("EPSG::4326")
        elif crs_data == "Local":
            target_crs = None # None implies Local in some contexts? Or we just clear crs.
            # Usually Metashape.CoordinateSystem can be None for strict local, or constructed local.
            # If target_crs is None, we set chunk.crs = None? No, better to keep it None.
        
        # Get Column Mapping (1-based index from UI -> 0-based for list)
        col_label = self.spin_col_label.value() - 1
        col_x = self.spin_col_x.value() - 1
        col_y = self.spin_col_y.value() - 1
        col_z = self.spin_col_z.value() - 1
        col_acc = self.spin_col_acc.value() - 1
        use_acc = self.cb_acc.isChecked()
        start_row = self.spin_start_row.value() - 1 # 0-indexed logic
        
        # Read All Data
        marker_data = {} # Label -> {loc: Vector, acc: float}
        with open(self.csv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f) # Default comma
            for i, row in enumerate(reader):
                if i < start_row: continue
                if not row: continue
                
                try:
                    label = row[col_label].strip()
                    x = float(row[col_x])
                    y = float(row[col_y])
                    z = float(row[col_z])
                    
                    data = {'loc': Metashape.Vector((x,y,z))}
                    
                    if use_acc and len(row) > col_acc:
                         data['acc'] = float(row[col_acc])
                    
                    marker_data[label] = data
                except (ValueError, IndexError):
                    continue

        # Apply to Chunks
        root = self.tree.invisibleRootItem()
        modified_chunks = 0
        
        for i in range(root.childCount()):
            chunk_item = root.child(i)
            if chunk_item.checkState(0) != Qt.Checked:
                continue
            
            chunk_key = chunk_item.data(0, Qt.UserRole)
            chunk = next((c for c in Metashape.app.document.chunks if c.key == chunk_key), None)
            if not chunk: continue
            
            # Update Chunk CRS
            if target_crs:
                chunk.crs = target_crs
            else:
                chunk.crs = None # Local?
            
            chunk_modified = False
            for marker in chunk.markers:
                if marker.label in marker_data:
                    info = marker_data[marker.label]
                    marker.reference.location = info['loc']
                    if 'acc' in info:
                        marker.reference.accuracy = info['acc']
                    marker.reference.enabled = True
                    chunk_modified = True
            
            if chunk_modified:
                modified_chunks += 1

        self.refresh_tree_data()
        QMessageBox.information(self, "Success", f"Imported reference for {len(marker_data)} markers in {modified_chunks} chunks.")

def create_batch_marker_manager():
    app = Metashape.app
    from PySide2.QtWidgets import QApplication
    parent = QApplication.activeWindow()
    dlg = BatchMarkerManager(parent)
    dlg.exec_()
