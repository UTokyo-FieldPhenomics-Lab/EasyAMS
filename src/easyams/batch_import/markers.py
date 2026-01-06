import os
import csv
from PySide2.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                              QTreeWidget, QTreeWidgetItem, QLabel, QCheckBox, 
                              QTabWidget, QWidget, QListWidget, QLineEdit, 
                              QTableWidget, QTableWidgetItem, QComboBox, 
                              QSpinBox, QGroupBox, QFileDialog, QMessageBox, QSplitter,
                              QHeaderView, QAbstractItemView, QGridLayout)
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
        self.splitter.addWidget(self.tabs)
        
        # Initialize Data
        self.refresh_tree_data()
        
        # Add Tabs
        self.init_tab1_manage()
        self.tabs.addTab(self.tab1, "Manage Markers")
        self.init_tab2_rename()
        self.tabs.addTab(self.tab2, "Rename")
        self.init_tab3_import()
        self.tabs.addTab(self.tab3, "Import CSV")

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
        item.setText(0, "📍 " + marker.label)
        
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

    # --- Tab 1: Manage Markers ---
    def init_tab1_manage(self):
        self.tab1 = QWidget()
        layout = QVBoxLayout()
        self.tab1.setLayout(layout)
        
        layout.addWidget(QLabel("Unique Markers across all chunks:"))
        self.marker_list = QListWidget()
        self.marker_list.setSelectionMode(QListWidget.ExtendedSelection)
        layout.addWidget(self.marker_list)
        
        btn_layout = QHBoxLayout()
        self.input_add_marker = QLineEdit()
        self.input_add_marker.setPlaceholderText("New Marker Name")
        self.btn_add_marker = QPushButton("Add")
        self.btn_add_marker.clicked.connect(self.add_marker_to_list)
        
        self.btn_remove_marker = QPushButton("Remove Selected")
        self.btn_remove_marker.clicked.connect(self.remove_marker_from_list)
        
        btn_layout.addWidget(self.input_add_marker)
        btn_layout.addWidget(self.btn_add_marker)
        btn_layout.addWidget(self.btn_remove_marker)
        layout.addLayout(btn_layout)
        
        action_layout = QHBoxLayout()
        self.btn_preview_changes = QPushButton("Preview Changes")
        self.btn_preview_changes.clicked.connect(self.preview_changes_tab1)
        
        self.btn_apply_changes = QPushButton("Apply Changes")
        self.btn_apply_changes.clicked.connect(self.apply_changes_tab1)
        
        action_layout.addWidget(self.btn_preview_changes)
        action_layout.addWidget(self.btn_apply_changes)
        layout.addLayout(action_layout)

        self.populate_unique_markers()

    def populate_unique_markers(self):
        unique_names = set()
        for chunk in self.get_all_chunks():
            for marker in chunk.markers:
                unique_names.add(marker.label)
        
        self.marker_list.clear()
        self.original_unique_markers = sorted(list(unique_names))
        self.marker_list.addItems(self.original_unique_markers)

    def add_marker_to_list(self):
        name = self.input_add_marker.text().strip()
        if name and not self.marker_list.findItems(name, Qt.MatchExactly):
            self.marker_list.addItem(name)
            self.input_add_marker.clear()

    def remove_marker_from_list(self):
        for item in self.marker_list.selectedItems():
            self.marker_list.takeItem(self.marker_list.row(item))

    def preview_changes_tab1(self):
        current_markers = set(self.marker_list.item(i).text() for i in range(self.marker_list.count()))
        original_markers = set(self.original_unique_markers)
        
        added = current_markers - original_markers
        removed = original_markers - current_markers
        
        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            chunk_item = root.child(i)
            
            # Reset existing styles
            for j in range(chunk_item.childCount()):
                child = chunk_item.child(j)
                text = child.text(0)
                # Clean name
                name = text.replace("📍 ", "").replace("➕ ", "").strip()
                
                if name in removed:
                    child.setForeground(0, Qt.red)
                    font = child.font(0)
                    font.setStrikeOut(True)
                    child.setFont(0, font)
                else:
                    child.setForeground(0, Qt.black)
                    font = child.font(0)
                    font.setStrikeOut(False)
                    child.setFont(0, font)

            # Add new items preview (only if not already there to avoid duplicates)
            current_children_names = set()
            for j in range(chunk_item.childCount()):
                txt = chunk_item.child(j).text(0)
                current_children_names.add(txt.replace("📍 ", "").replace("➕ ", "").strip())

            for new_marker in added:
                if new_marker not in current_children_names:
                    item = QTreeWidgetItem(chunk_item)
                    item.setText(0, f"➕ {new_marker}")
                    item.setForeground(0, Qt.green)
                    for col in range(1, 7):
                        item.setText(col, "-")

    def apply_changes_tab1(self):
        current_markers = set(self.marker_list.item(i).text() for i in range(self.marker_list.count()))
        original_markers = set(self.original_unique_markers)
        
        added = current_markers - original_markers
        removed = original_markers - current_markers
        
        root = self.tree.invisibleRootItem()
        modified_chunks = 0
        
        for i in range(root.childCount()):
            chunk_item = root.child(i)
            if chunk_item.checkState(0) != Qt.Checked:
                continue
                
            chunk_key = chunk_item.data(0, Qt.UserRole)
            chunk = None
            for c in Metashape.app.document.chunks:
                if c.key == chunk_key:
                    chunk = c
                    break
            
            if not chunk: continue
            
            for marker in list(chunk.markers):
                if marker.label in removed:
                    chunk.remove(marker)
            
            for name in added:
                existing = [m for m in chunk.markers if m.label == name]
                if not existing:
                    m = chunk.addMarker()
                    m.label = name
            
            modified_chunks += 1

        self.refresh_tree_data()
        self.populate_unique_markers()
        QMessageBox.information(self, "Success", f"Applied changes to {modified_chunks} chunks.")

    # --- Tab 2: Rename Markers ---
    def init_tab2_rename(self):
        self.tab2 = QWidget()
        layout = QVBoxLayout()
        self.tab2.setLayout(layout)
        
        # Inputs
        input_layout = QHBoxLayout()
        self.input_rename_from = QLineEdit()
        self.input_rename_from.setPlaceholderText("Find (substring)")
        self.input_rename_to = QLineEdit()
        self.input_rename_to.setPlaceholderText("Replace with")
        
        input_layout.addWidget(QLabel("Find:"))
        input_layout.addWidget(self.input_rename_from)
        input_layout.addWidget(QLabel("Replace:"))
        input_layout.addWidget(self.input_rename_to)
        layout.addLayout(input_layout)
        
        # Lists
        lists_layout = QHBoxLayout()
        
        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("Original Names"))
        self.list_rename_original = QListWidget()
        left_layout.addWidget(self.list_rename_original)
        
        right_layout = QVBoxLayout()
        right_layout.addWidget(QLabel("Preview Result"))
        self.list_rename_preview = QListWidget()
        right_layout.addWidget(self.list_rename_preview)
        
        lists_layout.addLayout(left_layout)
        lists_layout.addLayout(right_layout)
        layout.addLayout(lists_layout)
        
        # Buttons
        btn_layout = QHBoxLayout()
        self.btn_rename_preview = QPushButton("Preview Rename")
        self.btn_rename_preview.clicked.connect(self.preview_rename)
        self.btn_rename_reset = QPushButton("Reset")
        self.btn_rename_reset.clicked.connect(self.reset_rename)
        self.btn_rename_apply = QPushButton("Apply Rename")
        self.btn_rename_apply.clicked.connect(self.apply_rename)
        
        btn_layout.addWidget(self.btn_rename_preview)
        btn_layout.addWidget(self.btn_rename_reset)
        btn_layout.addWidget(self.btn_rename_apply)
        layout.addLayout(btn_layout)
        
        # Populate initial list (using shared unique markers if available, else refresh)
        if hasattr(self, 'original_unique_markers'):
             self.list_rename_original.addItems(self.original_unique_markers)
             self.list_rename_preview.addItems(self.original_unique_markers)
        else:
             self.populate_unique_markers() # This updates shared list, need to sync
             self.list_rename_original.addItems(self.original_unique_markers)
             self.list_rename_preview.addItems(self.original_unique_markers)

    def preview_rename(self):
        find_str = self.input_rename_from.text()
        replace_str = self.input_rename_to.text()
        
        self.list_rename_preview.clear()
        
        for i in range(self.list_rename_original.count()):
            original_name = self.list_rename_original.item(i).text()
            new_name = original_name.replace(find_str, replace_str)
            self.list_rename_preview.addItem(new_name)
            
            # Highlight changes
            if new_name != original_name:
                self.list_rename_preview.item(i).setForeground(Qt.blue)

    def reset_rename(self):
        self.input_rename_from.clear()
        self.input_rename_to.clear()
        self.list_rename_preview.clear()
        for i in range(self.list_rename_original.count()):
            self.list_rename_preview.addItem(self.list_rename_original.item(i).text())

    def apply_rename(self):
        count = self.list_rename_original.count()
        renames = {} # old -> new
        
        for i in range(count):
            old = self.list_rename_original.item(i).text()
            new = self.list_rename_preview.item(i).text()
            if old != new:
                renames[old] = new
        
        if not renames:
            return

        modified_chunks = 0
        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            chunk_item = root.child(i)
            if chunk_item.checkState(0) != Qt.Checked:
                continue
            
            chunk_key = chunk_item.data(0, Qt.UserRole)
            chunk = next((c for c in Metashape.app.document.chunks if c.key == chunk_key), None)
            if not chunk: continue
            
            chunk_modified = False
            for marker in chunk.markers:
                if marker.label in renames:
                    marker.label = renames[marker.label]
                    chunk_modified = True
            
            if chunk_modified:
                modified_chunks += 1
                
        self.refresh_tree_data()
        self.populate_unique_markers()
        # Refresh lists in rename tab too
        self.list_rename_original.clear()
        self.list_rename_preview.clear()
        self.list_rename_original.addItems(self.original_unique_markers)
        self.list_rename_preview.addItems(self.original_unique_markers)
        
        QMessageBox.information(self, "Success", f"Renamed markers in {modified_chunks} chunks.")

    # --- Tab 3: Import Reference ---
    def init_tab3_import(self):
        self.tab3 = QWidget()
        layout = QVBoxLayout()
        self.tab3.setLayout(layout)
        
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
        self.btn_import_reset.clicked.connect(self.reset_tab3)
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

    def reset_tab3(self):
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
