import os
from PySide2.QtWidgets import (QWidget, QApplication, QVBoxLayout, QHBoxLayout, QPushButton, 
                              QTreeWidget, QTreeWidgetItem, QTreeWidgetItemIterator, QFileDialog,
                              QCheckBox, QLabel, QMessageBox, QDialog)
from PySide2.QtCore import Qt, Signal
from PySide2.QtGui import QColor, QBrush
import Metashape

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
        """Recursively scan folders for mask images"""
        self.mask_map = {}
        for root, dirs, files in os.walk(self.root_path):
            for f in files:
                if f.lower().endswith(self.mask_exts):
                    stem = os.path.splitext(f)[0]
                    # If duplicate names exist, last one wins or we warn? 
                    # User said "Image Name as unique id". Assuming uniqueness.
                    self.mask_map[stem] = {
                        'path': os.path.join(root, f),
                        'dir': root,
                        'ext': os.path.splitext(f)[1]
                    }

    def match_masks(self):
        """Match scanned masks to tree items"""
        iterator = QTreeWidgetItemIterator(self.tree_widget)
        while iterator.value():
            item = iterator.value()
            if item.data(0, Qt.UserRole + 99) == "image":
                cam_label = item.data(0, Qt.UserRole + 10)
                # Metashape camera labels often include extension (e.g. "DSC01.JPG")
                # We strictly match by STEM.
                cam_stem = os.path.splitext(cam_label)[0]
                
                # Check match
                if cam_stem in self.mask_map:
                    # Matched
                    mask_info = self.mask_map[cam_stem]
                    item.setText(0, f"🖼 {cam_label} (matched)")
                    item.setForeground(0, QBrush(QColor("black")))
                    item.setData(0, Qt.UserRole + 20, mask_info) # Store mask info
                else:
                    # Missing
                    # item.setText(0, f"🖼 {cam_label}") 
                    # User: "if missing, the full image name become red, (missing) stay black"
                    # NOTE: QTreeWidgetItem color applies to the whole column text usually.
                    # QTreeWidget doesn't support partial coloring easily. 
                    # We will color the whole line red as a compromise, or use HTML?
                    # QTreeWidget items standardly don't render HTML unless a delegate is set or RichText flag?
                    # But setText usually treats as plain text. 
                    # Let's try coloring the whole item red as originally planned/implemented, 
                    # but append (missing).
                    item.setText(0, f"🖼 {cam_label} (missing)") 
                    item.setForeground(0, QBrush(QColor("red")))
                    item.setData(0, Qt.UserRole + 20, None)
            
            iterator += 1

    def import_masks(self):
        """Perform the import"""
        if not self.root_path:
            return

        doc = Metashape.app.document
        
        # Collect matched tasks
        # { (mask_dir, mask_ext): [camera_obj_list] }
        import_groups = {}
        
        # We need to map item -> camera object
        # Since tree items are subsets (only head/tail), we cannot rely ONLY on tree items 
        # if we want to import for ALL cameras.
        # WAIT. The tree only shows head/tail. But the USER might expect ALL cameras to be processed.
        # Logic: 
        # 1. We should scan ALL cameras in the actual chunks, not just tree items.
        # 2. Use tree items only for PREVIEW of matching status.
        # 3. But the User can UNCHECK tree items (chunks/groups). Use this to filter.
        
        # Helper to check if a chunk/group is enabled.
        # Since we use Tristate, we check top-level Chunks and Groups.
        
        # Let's iterate Chunks in Doc
        tasks_count = 0
        
        iterator = QTreeWidgetItemIterator(self.tree_widget)
        # Build set of unchecked keys (Chunks/Groups)
        # Actually it's easier to verify "Is Checked" from UI? 
        # But UI only has partial list.
        # User experience: If I uncheck a Group in UI, I expect NO cameras in that group to import.
        # So we must map UI state back to model.
        
        # Map IDs to CheckState
        active_chunks = set() # keys
        active_groups = set() # keys
        
        # Iterate top level
        root = self.tree_widget.invisibleRootItem()
        for i in range(root.childCount()):
            chunk_item = root.child(i)
            chunk_key = chunk_item.data(0, Qt.UserRole)
            
            if chunk_item.checkState(0) != Qt.Unchecked: # Checked or PartiallyChecked
                active_chunks.add(chunk_key)
                
                # Check groups
                for j in range(chunk_item.childCount()):
                    child_item = chunk_item.child(j)
                    # Check if it is a group (has UserRole for group key) or generic image list container?
                    # In my structure, Image Items are direct children of Chunk if no group. 
                    # Group Items are children if group.
                    
                    # Distinguish Group from Image
                    if child_item.data(0, Qt.UserRole + 99) == "image":
                        # Direct image under chunk. 
                        # If Chunk is checked, we assume we process these images.
                        # Do we support unchecking individual images? 
                        # The UI allows it, but since we don't show ALL images, we can't uncheck hidden ones.
                        # Assumption: If parent (Chunk/Group) is checked, we process ALL its cameras 
                        # UNLESS explicitly unchecked in UI? 
                        # Use "Group/Chunk" level granularity for "hidden" items.
                        # For "visible" items, we can respect individual checks? 
                        # That complicates it. 
                        # Simplification: Import follows Chunk/Group check state. 
                        # If a user unchecks a specific visible image, we skip it.
                        pass
                    else:
                        # This is a Group
                        group_key = child_item.data(0, Qt.UserRole)
                        if child_item.checkState(0) == Qt.Checked:
                            active_groups.add(group_key)

        # Now processing
        try:
            for chunk in doc.chunks:
                if chunk.key not in active_chunks:
                    continue
                
                chunk_cameras = []
                
                # Iterate all cameras in chunk
                for camera in chunk.cameras:
                    # Check Group filtering
                    if camera.group:
                        if camera.group.key not in active_groups:
                            continue
                    else:
                        # If it's ungrouped, we rely on Chunk being active. 
                        # But wait, if chunk is "Partially Checked" because some groups are off, 
                        # are ungrouped images included? 
                        # Usually yes, unless we had a specific "Ungrouped" container in UI. 
                        # In my code: `_add_camera_items(chunk_item, ungrouped_cameras)`.
                        # So they are direct children. If Chunk is Checked/Partial, we usually include them.
                        pass
                    
                    # Match Mask
                    # Use stem lookup
                    cam_stem = os.path.splitext(camera.label)[0]
                    if cam_stem in self.mask_map:
                        mask_info = self.mask_map[cam_stem]
                        path_key = (mask_info['dir'], mask_info['ext'])
                        
                        if path_key not in import_groups:
                            import_groups[path_key] = []
                        import_groups[path_key].append(camera)
                        tasks_count += 1
            
            # Execute Imports
            if tasks_count == 0:
                QMessageBox.information(self, "Info", "No matching masks found for selected cameras.")
                return

            # Progress bar? Metashape calls are blocking.
            
            for (mask_dir, mask_ext), cameras in import_groups.items():
                if not cameras: 
                    continue
                    
                # Find chunk for these cameras. 
                # generateMasks is a Chunk method, but takes a list of cameras. 
                # All cameras in the list MUST belong to the chunk.
                # So we must further subgroup by Chunk.
                
                chunk_groups = {} # {chunk_key: [cameras]}
                for cam in cameras:
                    c_chunk = cam.chunk
                    if c_chunk.key not in chunk_groups:
                        chunk_groups[c_chunk.key] = []
                    chunk_groups[c_chunk.key].append(cam)
                
                for c_key, c_cams in chunk_groups.items():
                    # Pick the chunk from the first camera (they are all same chunk object ref usually)
                    # or lookup by key from doc (safer if doc reloaded? No, obj ref is fine)
                    op_chunk = c_cams[0].chunk
                    
                    # Pattern
                    template = os.path.join(mask_dir, f"{{filename}}{mask_ext}")
                    
                    op_chunk.generateMasks(path=template, 
                                         masking_mode=Metashape.MaskingModeFile, 
                                         cameras=c_cams)
            
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
