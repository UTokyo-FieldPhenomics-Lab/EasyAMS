import os
import json
from PySide2.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                              QTreeWidget, QTreeWidgetItem, QFileDialog,
                              QCheckBox, QLabel, QMessageBox, QDialog, QScrollArea)
from PySide2.QtCore import Qt
import Metashape

from .utils import PathManager

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
        self.img_ext = ('.jpg', '.jpeg', '.png', '.tif', '.tiff')

        self.path_manager = PathManager()
    
    def select_folder(self):
        last_path = self.path_manager.load_last_batch_import_path()
        folder = QFileDialog.getExistingDirectory(self, "Select Root Image Folder", dir=last_path)

        if folder:
            self.path_manager.save_last_batch_import_path(folder)

            self.root_path = folder
            self.folder_path.setText(folder)
            self.update_preview()
            self.import_btn.setEnabled(True)


    def get_folder_structure(self, root_path, use_camera_groups):
        """Shared function to scan folder structure and return organized data"""
        structure = {
            'chunks': [],
        }

        # Build regular structure
        for item in os.listdir(root_path):
            item_path = os.path.join(root_path, item)
            if os.path.isdir(item_path):
                chunk_data = {
                    'name': item,
                    'path': item_path,
                    'groups': []
                }
                if use_camera_groups:
                    for sub_item in os.listdir(item_path):
                        sub_item_path = os.path.join(item_path, sub_item)
                        if os.path.isdir(sub_item_path):
                            group_data = {
                                'name': sub_item,
                                'path': sub_item_path,
                                'images': [f for f in os.listdir(sub_item_path) 
                                        if f.lower().endswith(self.img_ext)]
                            }
                            chunk_data['groups'].append(group_data)
                else:
                    chunk_data['images'] = [f for f in os.listdir(item_path) 
                                        if f.lower().endswith(self.img_ext)]
                structure['chunks'].append(chunk_data)

        return structure
    

    def update_preview(self):
        """Update the tree widget preview with checkboxes for folder selection"""

        if not self.root_path:
            return
            
        self.tree_widget.clear()
        use_camera_groups = self.camera_group_cb.isChecked()
        structure = self.get_folder_structure(self.root_path, use_camera_groups)

        self.ignored_folders = set()  # 存储用户选择忽略的文件夹
        
        try:
            for chunk in structure['chunks']:
                # 检查chunk是否有效（包含图片或有效group）
                is_valid_chunk = bool(chunk['images']) if not use_camera_groups else any(group['images'] for group in chunk['groups'])
            
                # Add chunk item with checkbox
                chunk_item = QTreeWidgetItem(self.tree_widget)

                chunk_suffix = "Chunk" if is_valid_chunk else "invalid chunk without images"

                chunk_item.setText(0, f"📁 {chunk['name']} ({chunk_suffix})")
                chunk_item.setCheckState(0, Qt.Checked if is_valid_chunk else Qt.Unchecked)
                chunk_item.setData(0, Qt.UserRole, chunk['path'])  # 存储完整路径

                if not is_valid_chunk:
                    chunk_item.setFlags(chunk_item.flags() & ~Qt.ItemIsEnabled)  # 禁用无效chunk
                    continue
                    
                if use_camera_groups:
                    # Add camera groups with checkboxes
                    for group in chunk['groups']:
                        is_valid_group = bool(group['images'])

                        group_item = QTreeWidgetItem(chunk_item)
                        group_suffix = "Camera Group" if is_valid_group else "invalid camera group without images"

                        group_item.setText(0, f"📷 {group['name']} ({group_suffix})")
                        group_item.setCheckState(0, Qt.Checked if is_valid_group else Qt.Unchecked)
                        group_item.setData(0, Qt.UserRole, group['path'])

                        if not is_valid_group:
                            group_item.setFlags(group_item.flags() & ~Qt.ItemIsEnabled)  # 禁用无效group
                            continue
                            
                        # Add sample images (no checkboxes for images)
                        for img in group['images'][:3]:  # Show first 3 as sample
                            img_item = QTreeWidgetItem(group_item)
                            img_item.setText(0, f"🖼 {img}")
                        if len(group['images']) > 3:
                            more_item = QTreeWidgetItem(group_item)
                            more_item.setText(0, f"... and {len(group['images'])-3} more")
                else:
                    # Add images directly under chunk (no checkboxes for images)
                    images = chunk.get('images', [])
                    for img in images[:5]:
                        img_item = QTreeWidgetItem(chunk_item)
                        img_item.setText(0, f"🖼 {img}")
                    if len(images) > 5:
                        more_item = QTreeWidgetItem(chunk_item)
                        more_item.setText(0, f"... and {len(images)-5} more")
            
            # 连接itemChanged信号以跟踪复选框状态变化<sup>1</sup>
            self.tree_widget.itemChanged.connect(self.on_item_changed)
            self.tree_widget.expandAll()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error scanning folder: {str(e)}")

    def on_item_changed(self, item, column):
        """Handle checkbox state changes"""
        state = item.checkState(0)

        # 同步子项状态
        if item.parent() is None:  # 如果是chunk顶级项
            for i in range(item.childCount()):
                child = item.child(i)
                child.setCheckState(0, state)

                if state == Qt.Unchecked:
                    self.ignored_folders.add(child.data(0, Qt.UserRole))
                else:
                    self.ignored_folders.discard(child.data(0, Qt.UserRole))

        if state == Qt.Unchecked:
            self.ignored_folders.add(item.data(0, Qt.UserRole))  # 添加到忽略列表<sup>1</sup>
        else:
            self.ignored_folders.discard(item.data(0, Qt.UserRole))  # 从忽略列表移除<sup>1</sup>

    def get_ignored_folders(self):
        """Return the list of folders marked for ignoring"""
        return list(self.ignored_folders)

    
    def import_images(self):
        """Perform the actual import"""
        if not self.root_path:
            return
        
        doc = Metashape.app.document
            
        use_camera_groups = self.camera_group_cb.isChecked()
        structure = self.get_folder_structure(self.root_path, use_camera_groups)
        
        try:
            for chunk in structure['chunks']:
                # 跳过未选中的chunk
                chunk_path = os.path.join(self.root_path, chunk['name'])
                if chunk_path in self.ignored_folders:
                    continue
            
                # Create new chunk
                ms_chunk = doc.addChunk()
                ms_chunk.label = chunk['name']
                
                if use_camera_groups and chunk['groups']:
                    # Add camera groups
                    for group in chunk['groups']:

                        # 跳过未选中的group
                        group_path = os.path.join(chunk_path, group['name'])
                        if group_path in self.ignored_folders:
                            continue

                        if group['images']:
                            # Create camera group
                            camera_group = ms_chunk.addCameraGroup()
                            camera_group.label = group['name']
                            
                            # Add images to group <sup>1</sup>
                            image_paths = [os.path.join(group['path'], img) for img in group['images']]
                            ms_chunk.addPhotos(image_paths, group=camera_group.key) 

                else:
                    # Add images directly to chunk
                    images = chunk.get('images', [])
                    if images:
                        image_paths = [os.path.join(chunk['path'], img) for img in images]
                        ms_chunk.addPhotos(image_paths)

            QMessageBox.information(self, "Success", "Images imported successfully!")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error during import: {str(e)}")

    
    def import_multi_camera(self, path, chunk_name):
        """Handle multi-camera system import (not implemented)"""
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
<pre>
Root/
├── Chunk1/ (becomes chunk)
│   ├── image1.jpg
│   └── image2.jpg
└── Chunk2/
    ├── image1.jpg
    └── image2.jpg
</pre>
        </p>
        
        <p><b>With camera groups:</b><br>
<pre>
Root/
├── Chunk1/ (becomes chunk)
│   ├── Group1/ (becomes camera group)
│   │   ├── image1.jpg
│   │   └── image2.jpg
│   └── Group2/
│       ├── image1.jpg
│       └── image2.jpg
└── Chunk2/
    ├── Group1/
    │   ├── image1.jpg
    │   └── image2.jpg
    └── Group2/
        ├── image1.jpg
        └── image2.jpg
</pre>
        </p>
        
        <h3>Multi-camera Systems:</h3>
        <p>Importing multi-camera systems have not been supported yet. This plugin is currently designed for RGB cameras only.</p>
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
