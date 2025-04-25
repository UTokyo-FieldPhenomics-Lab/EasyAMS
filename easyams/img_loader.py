import os
from PySide2.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                              QTreeWidget, QTreeWidgetItem, QFileDialog, 
                              QCheckBox, QLabel, QMessageBox, QDialog, QScrollArea)
from PySide2.QtCore import Qt
import Metashape

class BatchImageLoader(QDialog):  # 继承自QDialog
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setModal(True)  # 设置为模态对话框

        self.setWindowTitle("Batch Image Loader")
        self.setMinimumSize(600, 800)
        
        # Main layout
        self.layout = QVBoxLayout()
        
        # Folder selection
        self.folder_layout = QHBoxLayout()
        self.folder_label = QLabel("Root Folder:")
        self.folder_path = QLabel("No folder selected")
        self.select_folder_btn = QPushButton("Browse...")
        self.select_folder_btn.clicked.connect(self.select_folder)
        
        self.folder_layout.addWidget(self.folder_label)
        self.folder_layout.addWidget(self.folder_path)
        self.folder_layout.addWidget(self.select_folder_btn)
        
        # Camera group checkbox
        self.camera_group_cb = QCheckBox("Use second-level folders as camera groups")
        self.camera_group_cb.stateChanged.connect(self.update_preview)
        
        # Preview tree
        self.preview_label = QLabel("Import Preview:")
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabel("Workspace Structure")
        
        # Help button
        self.help_btn = QPushButton("Help")
        self.help_btn.clicked.connect(self.show_help)
        
        # Import button
        self.import_btn = QPushButton("Import Images")
        self.import_btn.clicked.connect(self.import_images)
        self.import_btn.setEnabled(False)
        
        # Add widgets to layout
        self.layout.addLayout(self.folder_layout)
        self.layout.addWidget(self.camera_group_cb)
        self.layout.addWidget(self.preview_label)
        self.layout.addWidget(self.tree_widget)
        self.layout.addWidget(self.help_btn)
        self.layout.addWidget(self.import_btn)
        
        self.setLayout(self.layout)
        
        # Variables
        self.root_path = ""
        self.multi_camera_dirs = []
    
    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Root Image Folder")
        if folder:
            self.root_path = folder
            self.folder_path.setText(folder)
            self.scan_folder_structure()
            self.update_preview()
            self.import_btn.setEnabled(True)
    
    def scan_folder_structure(self):
        """Scan for potential multi-camera directories"""
        self.multi_camera_dirs = []
        
        for root, dirs, files in os.walk(self.root_path):
            # Check if this might be a multi-camera setup
            if all(os.path.isdir(os.path.join(root, d)) for d in dirs):
                image_counts = []
                for d in dirs:
                    subdir = os.path.join(root, d)
                    image_count = len([f for f in os.listdir(subdir) 
                                     if f.lower().endswith(('.jpg', '.jpeg', '.png', '.tif', '.tiff'))])
                    image_counts.append(image_count)
                
                # If all subdirs have same number of images, might be multi-camera
                if len(set(image_counts)) == 1 and len(dirs) > 1:
                    self.multi_camera_dirs.append(root)
    

    def update_preview(self):
        """Update the tree widget preview"""
        if not self.root_path:
            return
            
        self.tree_widget.clear()
        
        use_camera_groups = self.camera_group_cb.isChecked()
        
        try:
            for item in os.listdir(self.root_path):
                item_path = os.path.join(self.root_path, item)
                if os.path.isdir(item_path):
                    # Add chunk item
                    chunk_item = QTreeWidgetItem(self.tree_widget)
                    chunk_item.setText(0, f"📁 {item} (Chunk)")
                    
                    if use_camera_groups:
                        # Add camera groups
                        for sub_item in os.listdir(item_path):
                            sub_item_path = os.path.join(item_path, sub_item)
                            if os.path.isdir(sub_item_path):
                                group_item = QTreeWidgetItem(chunk_item)
                                group_item.setText(0, f"📷 {sub_item} (Camera Group)")
                                
                                # Add sample images
                                images = [f for f in os.listdir(sub_item_path) 
                                         if f.lower().endswith(('.jpg', '.jpeg', '.png', '.tif', '.tiff'))]
                                for img in images[:3]:  # Show first 3 as sample
                                    img_item = QTreeWidgetItem(group_item)
                                    img_item.setText(0, f"🖼 {img}")
                                if len(images) > 3:
                                    more_item = QTreeWidgetItem(group_item)
                                    more_item.setText(0, f"... and {len(images)-3} more")
                    else:
                        # Add images directly under chunk
                        images = [f for f in os.listdir(item_path) 
                                 if f.lower().endswith(('.jpg', '.jpeg', '.png', '.tif', '.tiff'))]
                        for img in images[:5]:  # Show first 5 as sample
                            img_item = QTreeWidgetItem(chunk_item)
                            img_item.setText(0, f"🖼 {img}")
                        if len(images) > 5:
                            more_item = QTreeWidgetItem(chunk_item)
                            more_item.setText(0, f"... and {len(images)-5} more")
            
            self.tree_widget.expandAll()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error scanning folder: {str(e)}")
    
    def import_images(self):
        """Perform the actual import"""
        if not self.root_path:
            return
            
        use_camera_groups = self.camera_group_cb.isChecked()
        doc = Metashape.app.document
        
        try:
            for item in os.listdir(self.root_path):
                item_path = os.path.join(self.root_path, item)
                if os.path.isdir(item_path):
                    # Check if this is a multi-camera directory
                    if item_path in self.multi_camera_dirs:
                        self.import_multi_camera(item_path, item)
                        continue
                    
                    # Create new chunk
                    chunk = doc.addChunk()
                    chunk.label = item
                    
                    if use_camera_groups:
                        # Add camera groups
                        for sub_item in os.listdir(item_path):
                            sub_item_path = os.path.join(item_path, sub_item)
                            if os.path.isdir(sub_item_path):
                                # Create camera group
                                camera_group = chunk.addCameraGroup()
                                camera_group.label = sub_item
                                
                                # Add images to group
                                images = [os.path.join(sub_item_path, f) for f in os.listdir(sub_item_path) 
                                         if f.lower().endswith(('.jpg', '.jpeg', '.png', '.tif', '.tiff'))]
                                if images:
                                    chunk.addPhotos(images)
                                    # Assign cameras to group
                                    for camera in chunk.cameras[-len(images):]:
                                        camera.group = camera_group
                    else:
                        # Add images directly to chunk
                        images = [os.path.join(item_path, f) for f in os.listdir(item_path) 
                                 if f.lower().endswith(('.jpg', '.jpeg', '.png', '.tif', '.tiff'))]
                        if images:
                            chunk.addPhotos(images)
            
            QMessageBox.information(self, "Success", "Images imported successfully!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error during import: {str(e)}")

    
    def import_multi_camera(self, path, chunk_name):
        """Handle multi-camera system import <sup>2</sup>"""
        doc = Metashape.app.document
        chunk = doc.addChunk()
        chunk.label = chunk_name
        
        # Show dialog to confirm multi-camera import
        reply = QMessageBox.question(self, "Multi-camera System", 
                                    f"Folder '{chunk_name}' appears to contain images from a multi-camera system.\n"
                                    "Do you want to import these as a multi-camera rig?",
                                    QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            # Import as multi-camera system <sup>2</sup>
            chunk.addPhotos([os.path.join(path, f) for f in os.listdir(path) 
                           if os.path.isdir(os.path.join(path, f))], 
                          layout=Metashape.MultiplaneLayout)
        else:
            # Import as regular images
            images = []
            for root, dirs, files in os.walk(path):
                images.extend([os.path.join(root, f) for f in files 
                             if f.lower().endswith(('.jpg', '.jpeg', '.png', '.tif', '.tiff'))])
            if images:
                chunk.addPhotos(images)
    
    def show_help(self):
        """Show help dialog"""
        help_dialog = QDialog(self)
        help_dialog.setWindowTitle("Help")
        help_dialog.setMinimumSize(500, 400)
        
        layout = QVBoxLayout()
        scroll = QScrollArea()
        content = QWidget()
        content_layout = QVBoxLayout()
        
        help_text = QLabel("""
        <h2>Batch Image Loader Help</h2>
        <p>This tool allows you to import multiple folders of images into Metashape with automatic chunk and camera group creation.</p>
        
        <h3>Basic Usage:</h3>
        <ol>
            <li>Click "Browse..." to select the root folder containing your images</li>
            <li>Check "Use second-level folders as camera groups" if you want subfolders to become camera groups</li>
            <li>Review the import structure in the preview</li>
            <li>Click "Import Images" to perform the import</li>
        </ol>
        
        <h3>Folder Structure:</h3>
        <p><b>Without camera groups:</b><br>
        Root/<br>
        ├── Chunk1/ (becomes chunk)<br>
        │   ├── image1.jpg<br>
        │   └── image2.jpg<br>
        └── Chunk2/<br>
            ├── image1.jpg<br>
            └── image2.jpg</p>
        
        <p><b>With camera groups:</b><br>
        Root/<br>
        ├── Chunk1/ (becomes chunk)<br>
        │   ├── Group1/ (becomes camera group)<br>
        │   │   ├── image1.jpg<br>
        │   │   └── image2.jpg<br>
        │   └── Group2/<br>
        │       ├── image1.jpg<br>
        │       └── image2.jpg<br>
        └── Chunk2/<br>
            ├── Group1/<br>
            │   ├── image1.jpg<br>
            │   └── image2.jpg<br>
            └── Group2/<br>
                ├── image1.jpg<br>
                └── image2.jpg</p>
        
        <h3>Multi-camera Systems:</h3>
        <p>Folders that contain subfolders with equal numbers of images will be detected as potential multi-camera systems <sup>2</sup>. 
        You'll be prompted to confirm whether to import them as such.</p>
        """)
        help_text.setWordWrap(True)
        help_text.setTextFormat(Qt.RichText)
        
        content_layout.addWidget(help_text)
        content.setLayout(content_layout)
        scroll.setWidget(content)
        scroll.setWidgetResizable(True)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(help_dialog.close)
        
        layout.addWidget(scroll)
        layout.addWidget(close_btn)
        help_dialog.setLayout(layout)
        
        help_dialog.exec_()

def create_batch_image_loader():
    from PySide2 import QtWidgets
    app = QtWidgets.QApplication.instance()  # 获取当前Qt应用实例
    window = BatchImageLoader(app.activeWindow())
    window.exec_()  # 使用exec_()而非show()确保模态性
