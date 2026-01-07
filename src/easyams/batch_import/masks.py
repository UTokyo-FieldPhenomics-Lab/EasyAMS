import os
from PySide2.QtWidgets import (QWidget, QApplication, QVBoxLayout, QHBoxLayout, QPushButton, 
                              QTreeWidget, QTreeWidgetItem, QTreeWidgetItemIterator, QFileDialog,
                              QCheckBox, QLabel, QMessageBox, QDialog)
from PySide2.QtCore import Qt, Signal
from PySide2.QtGui import QColor, QBrush
import Metashape
from PIL import Image

class BatchMaskLoader(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setModal(True)

        self.setWindowTitle("Batch Mask Importer")
        self.setMinimumSize(600, 800)
        
        # Main layout
        self.layout = QVBoxLayout()
        
        # Note Label
        self.note_label = QLabel("<b>Note:</b> Mask filenames (without extension) MUST strictly match image filenames.<br>"
                               "Folder structure consistency is NOT required (images find masks by unique name).")
        self.note_label.setTextFormat(Qt.RichText)
        self.note_label.setStyleSheet("color: #555; margin-bottom: 10px;")
        
        # Folder selection
        self.folder_layout = QHBoxLayout()
        self.folder_label = QLabel("Mask Root Folder:")
        self.folder_path = QLabel("No folder selected")
        self.select_folder_btn = QPushButton("Browse...")
        self.select_folder_btn.clicked.connect(self.select_folder)
        
        self.folder_layout.addWidget(self.folder_label)
        self.folder_layout.addWidget(self.folder_path)
        self.folder_layout.addWidget(self.select_folder_btn)
        
        # Preview tree controls
        self.preview_layout = QHBoxLayout()
        self.preview_label = QLabel("Import Preview:")

        self.btn_expand_all = QPushButton("Expand All")
        self.btn_expand_all.clicked.connect(self.expand_all_items)
        self.btn_collapse_all = QPushButton("Collapse All")
        self.btn_collapse_all.clicked.connect(self.collapse_all_items)

        self.btn_select_all = QPushButton("Select All")
        self.btn_select_all.clicked.connect(self.select_all_items)
        self.btn_clear_all = QPushButton("Clear")
        self.btn_clear_all.clicked.connect(self.clear_all_items)

        self.preview_layout.addWidget(self.preview_label)
        self.preview_layout.addStretch()
        self.preview_layout.addWidget(self.btn_expand_all)
        self.preview_layout.addWidget(self.btn_collapse_all)
        self.preview_layout.addWidget(self.btn_select_all)
        self.preview_layout.addWidget(self.btn_clear_all)

        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabel("Metashape Workspace Structure")
        
        # Help button
        self.help_btn = QPushButton("Help")
        self.help_btn.clicked.connect(self.show_help)
        
        # Import button
        self.import_btn = QPushButton("Import Masks")
        self.import_btn.clicked.connect(self.import_masks)
        self.import_btn.setEnabled(False)
        
        # Add widgets to layout
        self.layout.addWidget(self.note_label)
        self.layout.addLayout(self.folder_layout)
        self.layout.addLayout(self.preview_layout)
        self.layout.addWidget(self.tree_widget)
        self.layout.addWidget(self.help_btn)
        self.layout.addWidget(self.import_btn)
        
        self.setLayout(self.layout)
        
        # Variables
        self.root_path = ""
        self.mask_map = {} # {stem: {path: fullpath, ext: .png}}
        self.mask_exts = ('.jpg', '.jpeg', '.png', '.tif', '.tiff', '.bmp')

        from .. import system_info
        self.config_manager = system_info.config_manager

        # Initial Load of Structure (without match status)
        self.load_project_structure()

    def load_project_structure(self):
        """Load current Metashape project structure into tree"""
        self.tree_widget.clear()
        doc = Metashape.app.document
        
        for chunk in doc.chunks:
            chunk_item = QTreeWidgetItem(self.tree_widget)
            chunk_item.setText(0, f"📁 {chunk.label}")
            chunk_item.setData(0, Qt.UserRole, chunk.key) # Store chunk key/id
            chunk_item.setFlags(chunk_item.flags() | Qt.ItemIsUserCheckable)
            chunk_item.setCheckState(0, Qt.Checked)
            
            # Map cameras to groups
            # Structure: {group_id: [cameras], None: [cameras]}
            groups = {}
            ungrouped_cameras = []
            
            for camera in chunk.cameras:
                if camera.group:
                    if camera.group.key not in groups:
                        groups[camera.group.key] = {
                            'obj': camera.group,
                            'cameras': []
                        }
                    groups[camera.group.key]['cameras'].append(camera)
                else:
                    ungrouped_cameras.append(camera)
            
            # Add Groups
            for group_key, group_data in groups.items():
                group_obj = group_data['obj']
                cameras = group_data['cameras']
                
                group_item = QTreeWidgetItem(chunk_item)
                group_item.setText(0, f"📷 {group_obj.label}")
                group_item.setData(0, Qt.UserRole, group_obj.key)
                group_item.setFlags(group_item.flags() | Qt.ItemIsUserCheckable)
                group_item.setCheckState(0, Qt.Checked)
                
                self._add_camera_items(group_item, cameras)
                
            # Add Ungrouped Cameras
            if ungrouped_cameras:
                self._add_camera_items(chunk_item, ungrouped_cameras)
        
        self.tree_widget.expandAll()
        self.tree_widget.itemChanged.connect(self.on_item_changed)
    
    def _add_camera_items(self, parent_item, cameras):
        """Helper to add camera items with truncation"""
        # Show first 2
        for camera in cameras[:2]:
            cam_item = QTreeWidgetItem(parent_item)
            cam_item.setText(0, f"🖼 {camera.label}")
            cam_item.setData(0, Qt.UserRole, camera.key) # Store camera key
            cam_item.setData(0, Qt.UserRole + 10, camera.label) # Store camera label for matching
            # Mark as leaf image
            cam_item.setData(0, Qt.UserRole + 99, "image") 
            # Explicitly remove UserCheckable to prevent accidental checkbox appearance
            cam_item.setFlags(cam_item.flags() & ~Qt.ItemIsUserCheckable)
            
            # Initially enabled? Yes. But depends on parent check? 
            # Parent is checked by default, so we enable.
            pass

        if len(cameras) > 2:
            # Add ...
            dots_item = QTreeWidgetItem(parent_item)
            dots_item.setText(0, "...")
            dots_item.setFlags(Qt.NoItemFlags) # Disable interaction
            
            # Show last 2 (if different from first 2)
            # Actually, standard is First 2 ... Last 2. 
            # If len is 3, first 2, then last 1 (which duplicates index 2).
            # Let's simple slice: first 2, then dots, then last 2.
            # Handle overlap/small counts
            remaining = cameras[2:]
            if len(remaining) <= 2:
                # Just show them, no dots needed?
                # Actually if total > 4, we use dots? User req: "Image only show head and tail 2 sheets, middle omit with ..."
                pass
            
            # Correct logic:
            # If <= 4, show all.
            # If > 4, show 0,1, ..., -2, -1
            pass 

        # Re-implementing display logic more cleanly to match "head 2, tail 2"
        # First, clear the items I just added to redo logic properly if needed, 
        # but helper is called on empty parent usually.
        # Actually, let's just stick to the loop above for first 2, then handle tail.
        
        if len(cameras) > 4:
            # We already added first 2.
            # Add tail 2
            for camera in cameras[-2:]:
                cam_item = QTreeWidgetItem(parent_item)
                cam_item.setText(0, f"🖼 {camera.label}")
                cam_item.setData(0, Qt.UserRole, camera.key)
                cam_item.setData(0, Qt.UserRole + 10, camera.label)
                cam_item.setData(0, Qt.UserRole + 99, "image")
                # cam_item.setFlags(cam_item.flags() | Qt.ItemIsUserCheckable)
                # cam_item.setCheckState(0, Qt.Checked)
        elif len(cameras) > 2:
             # Just add the rest (3rd and/or 4th)
             for camera in cameras[2:]:
                cam_item = QTreeWidgetItem(parent_item)
                cam_item.setText(0, f"🖼 {camera.label}")
                cam_item.setData(0, Qt.UserRole, camera.key)
                cam_item.setData(0, Qt.UserRole + 10, camera.label)
                cam_item.setData(0, Qt.UserRole + 99, "image")
                # cam_item.setFlags(cam_item.flags() | Qt.ItemIsUserCheckable)
                # cam_item.setCheckState(0, Qt.Checked)
                
            # Remove the "..." item I added prematurely? 
            # My previous code added logic was linear. Let's fix the "..." insert.
            # I will refactor this slightly in the next pass or just correct purely here.
        
        # Real logic fix:
        child_count = parent_item.childCount()
        # Remove all children and rebuild to be safe
        parent_item.takeChildren()
        
        display_cameras = []
        if len(cameras) <= 4:
            display_cameras = cameras
            has_mid = False
        else:
            display_cameras = cameras[:2] + cameras[-2:]
            has_mid = True
            
        for i, camera in enumerate(display_cameras):
            if has_mid and i == 2:
                dots = QTreeWidgetItem(parent_item)
                dots.setText(0, "...")
                dots.setFlags(Qt.NoItemFlags)
                
            cam_item = QTreeWidgetItem(parent_item)
            cam_item.setText(0, f"🖼 {camera.label}")
            cam_item.setData(0, Qt.UserRole, camera.key)
            cam_item.setData(0, Qt.UserRole + 10, camera.label)
            cam_item.setData(0, Qt.UserRole + 99, "image")
            cam_item.setFlags(cam_item.flags() & ~Qt.ItemIsUserCheckable)


    def select_folder(self):
        last_path = self.config_manager.load('last_mask_import_folder')
        folder = QFileDialog.getExistingDirectory(self, "Select Mask Root Folder", dir=last_path)

        if folder:
            self.config_manager.save('last_mask_import_folder', folder)
            self.root_path = folder
            self.folder_path.setText(folder)
            self.scan_masks()
            self.match_masks()
            self.import_btn.setEnabled(True)

    def scan_masks(self):
        """Recursively scan folders for mask images.
        
        Stores list of candidates per stem to handle duplicates in different folders.
        """
        self.mask_map = {}  # {stem: [mask_info_list]}
        for root, dirs, files in os.walk(self.root_path):
            for f in files:
                if f.lower().endswith(self.mask_exts):
                    stem = os.path.splitext(f)[0]
                    mask_info = {
                        'path': os.path.join(root, f),
                        'dir': root,
                        'ext': os.path.splitext(f)[1]
                    }
                    if stem not in self.mask_map:
                        self.mask_map[stem] = []
                    self.mask_map[stem].append(mask_info)

    def match_masks(self):
        """Match scanned masks to tree items.
        
        For each camera, find a mask with matching stem AND resolution.
        If multiple candidates exist, select the first one with correct resolution.
        Results are cached in self.camera_match_cache for use during import.
        """
        doc = Metashape.app.document
        
        # Cache: {(chunk_key, camera_key): mask_info} for ALL cameras
        # Using composite key because camera.key is only unique within a chunk
        self.camera_match_cache = {}
        
        # Build camera key -> camera object map for resolution lookup
        camera_map = {}
        for chunk in doc.chunks:
            for camera in chunk.cameras:
                camera_map[camera.key] = camera
                
                # Pre-match ALL cameras (not just displayed ones)
                cam_stem = os.path.splitext(camera.label)[0]
                if cam_stem in self.mask_map:
                    candidates = self.mask_map[cam_stem]
                    if camera.sensor:
                        cam_width = camera.sensor.width
                        cam_height = camera.sensor.height
                        
                        # Build context labels for path matching priority
                        context_labels = [chunk.label]
                        if camera.group:
                            context_labels.append(camera.group.label)
                        
                        # First pass: find candidates matching resolution AND path context
                        matched_mask = None
                        for mask_info in candidates:
                            try:
                                with Image.open(mask_info['path']) as mask_img:
                                    mask_width, mask_height = mask_img.size
                                if cam_width == mask_width and cam_height == mask_height:
                                    # Check if path contains chunk/group label
                                    path_matches_context = any(
                                        label in mask_info['path'] for label in context_labels
                                    )
                                    if path_matches_context:
                                        matched_mask = mask_info
                                        break
                            except Exception:
                                continue
                        
                        # Second pass: if no context match, use any resolution match
                        if not matched_mask:
                            for mask_info in candidates:
                                try:
                                    with Image.open(mask_info['path']) as mask_img:
                                        mask_width, mask_height = mask_img.size
                                    if cam_width == mask_width and cam_height == mask_height:
                                        matched_mask = mask_info
                                        break
                                except Exception:
                                    continue
                        
                        if matched_mask:
                            self.camera_match_cache[(chunk.key, camera.key)] = matched_mask
        
        # Update tree display for visible items
        iterator = QTreeWidgetItemIterator(self.tree_widget)
        while iterator.value():
            item = iterator.value()
            if item.data(0, Qt.UserRole + 99) == "image":
                cam_label = item.data(0, Qt.UserRole + 10)
                cam_key = item.data(0, Qt.UserRole)
                cam_stem = os.path.splitext(cam_label)[0]
                
                # Need chunk_key for cache lookup - find parent chunk item
                parent = item.parent()
                while parent and parent.data(0, Qt.UserRole + 99) == "image":
                    parent = parent.parent()
                # parent is now either a Group or Chunk item
                if parent:
                    # If parent is a Group, get its parent (Chunk)
                    if parent.parent():
                        chunk_key = parent.parent().data(0, Qt.UserRole)
                    else:
                        chunk_key = parent.data(0, Qt.UserRole)
                else:
                    chunk_key = None
                
                cache_key = (chunk_key, cam_key) if chunk_key else None
                
                if cache_key and cache_key in self.camera_match_cache:
                    # Matched
                    item.setText(0, f"🖼 {cam_label} (matched)")
                    item.setForeground(0, QBrush(QColor("green")))
                    item.setData(0, Qt.UserRole + 20, self.camera_match_cache[cache_key])
                elif cam_stem in self.mask_map:
                    # Found candidates but none match resolution
                    item.setText(0, f"🖼 {cam_label} (resolution mismatch)")
                    item.setForeground(0, QBrush(QColor("red")))
                    item.setData(0, Qt.UserRole + 20, None)
                else:
                    # No mask found for this stem
                    item.setText(0, f"🖼 {cam_label} (missing)")
                    item.setForeground(0, QBrush(QColor("red")))
                    item.setData(0, Qt.UserRole + 20, None)
            
            iterator += 1

    def import_masks(self):
        """Perform the import using cached match results."""
        if not self.root_path:
            return
        
        if not hasattr(self, 'camera_match_cache') or not self.camera_match_cache:
            QMessageBox.warning(self, "Warning", "No matching masks found. Please select a mask folder first.")
            return

        doc = Metashape.app.document
        
        # Build active chunks/groups from UI
        active_chunks = set()
        active_groups = set()
        
        root = self.tree_widget.invisibleRootItem()
        for i in range(root.childCount()):
            chunk_item = root.child(i)
            chunk_key = chunk_item.data(0, Qt.UserRole)
            
            if chunk_item.checkState(0) != Qt.Unchecked:
                active_chunks.add(chunk_key)
                
                for j in range(chunk_item.childCount()):
                    child_item = chunk_item.child(j)
                    if child_item.data(0, Qt.UserRole + 99) != "image":
                        group_key = child_item.data(0, Qt.UserRole)
                        if child_item.checkState(0) == Qt.Checked:
                            active_groups.add(group_key)

        # Collect cameras to import using cached results
        # Group by (mask_dir, mask_ext, chunk_key) for batch processing
        import_groups = {}  # {(mask_dir, mask_ext, chunk_key): [cameras]}
        tasks_count = 0
        
        for chunk in doc.chunks:
            if chunk.key not in active_chunks:
                continue
            
            for camera in chunk.cameras:
                # Check Group filtering
                if camera.group:
                    if camera.group.key not in active_groups:
                        continue
                
                # Use cached match result with composite key
                cache_key = (chunk.key, camera.key)
                if cache_key in self.camera_match_cache:
                    mask_info = self.camera_match_cache[cache_key]
                    group_key = (mask_info['dir'], mask_info['ext'], chunk.key)
                    
                    if group_key not in import_groups:
                        import_groups[group_key] = []
                    import_groups[group_key].append(camera)
                    tasks_count += 1
        
        if tasks_count == 0:
            QMessageBox.information(self, "Info", "No matching masks found for selected cameras.")
            return

        try:
            # Execute batch import - one call per (mask_dir, mask_ext, chunk) combination
            for (mask_dir, mask_ext, chunk_key), cameras in import_groups.items():
                if not cameras:
                    continue
                
                op_chunk = cameras[0].chunk
                template = os.path.join(mask_dir, f"{{filename}}{mask_ext}")
                
                op_chunk.generateMasks(
                    path=template,
                    masking_mode=Metashape.MaskingModeFile,
                    cameras=cameras
                )
            
            QMessageBox.information(self, "Success", f"Imported masks for {tasks_count} cameras.")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")


    # Boilerplate Button Handlers
    def expand_all_items(self): self.tree_widget.expandAll()
    def collapse_all_items(self): self.tree_widget.collapseAll()
    def select_all_items(self): self._set_all_checkstate(Qt.Checked)
    def clear_all_items(self): self._set_all_checkstate(Qt.Unchecked)
    
    def _set_all_checkstate(self, state):
        root = self.tree_widget.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            item.setCheckState(0, state)
            # Children are auto-handled by on_item_changed usually, 
            # but if we change programmatically, we might need to recurse or let signal propagate?
            # Signal propagates if itemChanged is connected. 
            # But changing parent checkstate with Tristate set usually auto-updates children in QTreeWidget? 
            # No, standard QTreeWidget does NOT auto-propagate check changes to children. We have to do it.
            self._recursive_check(item, state)

    def _recursive_check(self, item, state):
        if item.flags() & Qt.ItemIsUserCheckable:
            item.setCheckState(0, state)
        for i in range(item.childCount()):
            self._recursive_check(item.child(i), state)

    def on_item_changed(self, item, column):
        # Handle Tristate logic for parents if needed, or propagation to children
        # Block signals to prevent recursion loops
        self.tree_widget.blockSignals(True)
        
        state = item.checkState(0)
        
        # Propagate down (Matching images.py logic)
        for i in range(item.childCount()):
            child = item.child(i)
            
            if state == Qt.Unchecked:
                 child.setFlags(child.flags() & ~Qt.ItemIsEnabled)
                 # Uncheck if checkable (like Group)
                 if child.flags() & Qt.ItemIsUserCheckable:
                     child.setCheckState(0, Qt.Unchecked)
                 
                 # Recurse if the child is a Group (which has children)
                 if child.childCount() > 0:
                     self._recursive_set_enabled(child, False)
                     
            elif state == Qt.Checked:
                 child.setFlags(child.flags() | Qt.ItemIsEnabled)
                 
                 # Check if checkable (Group)
                 if child.flags() & Qt.ItemIsUserCheckable:
                     child.setCheckState(0, Qt.Checked)
                     
                 if child.childCount() > 0:
                     self._recursive_set_enabled(child, True)

        self.tree_widget.blockSignals(False)

    def _recursive_set_enabled(self, item, enabled):
        """Helper to recursively enable/disable items"""
        # Set self
        if enabled:
            item.setFlags(item.flags() | Qt.ItemIsEnabled)
            if item.flags() & Qt.ItemIsUserCheckable:
                item.setCheckState(0, Qt.Checked)
        else:
            item.setFlags(item.flags() & ~Qt.ItemIsEnabled)
            if item.flags() & Qt.ItemIsUserCheckable:
                item.setCheckState(0, Qt.Unchecked)
            
        for i in range(item.childCount()):
            self._recursive_set_enabled(item.child(i), enabled)

    def show_help(self):
        QMessageBox.information(self, "Help", 
            "<h3>Batch Mask Importer</h3>"
            "<p>1. Select the root folder containing your masks.</p>"
            "<p>2. The tool scans for images matching your camera names.</p>"
            "<p>3. <b>Strict matching:</b> 'ImageName' must equal 'MaskName' (ignoring extension).</p>"
            "<p>4. Check matching status in the preview tree.</p>"
            "<p>5. Click Import to apply masks.</p>")

def create_batch_mask_importer():
    app = QApplication.instance()
    window = BatchMaskLoader(app.activeWindow())
    window.exec_()
