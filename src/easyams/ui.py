from PySide2 import QtWidgets, QtGui, QtCore
import Metashape

from . import img_loader, stag_gcp

def add_metashape_menu():
    # img loader function
    Metashape.app.addMenuItem("EasyAMS/batchImport/Import Images", img_loader.create_batch_image_loader)

    # stag_gcp function
    Metashape.app.addMenuItem("EasyAMS/StagMarkers/Detect Markers", stag_gcp.detect_stag_markers)
    Metashape.app.addMenuItem("EasyAMS/StagMarkers/Detect Markers in all chunks", stag_gcp.detect_all_stag_markers)
    # Metashape.app.addMenuItem("EasyAMS/StagMarkers/Print Markers", installer.print_paths)

    # -----------------------
    Metashape.app.addMenuSeparator("EasyAMS")

    # about easyams
    # Metashape.app.addMenuItem("EasyAMS/Check for Updates", installer.print_paths)
    Metashape.app.addMenuItem("EasyAMS/About EasyAMS", show_about_dialog)

def show_about_dialog():
    
    # 创建主对话框
    dialog = QtWidgets.QDialog()
    dialog.setWindowTitle("About EasyAMS")
    dialog.resize(400, 300)  # width, height
    # dialog.setSizeGripEnabled(True)  # 启用右下角的调整大小控件
    dialog.setMinimumSize(400, 300)  # 可选：设置最小大小
    dialog.setWindowIcon(QtGui.QIcon("/path/to/icon.png"))  # 替换为你的图标路径

    # 创建主布局
    layout = QtWidgets.QVBoxLayout(dialog)

    # 添加顶部图标和标题
    top_layout = QtWidgets.QHBoxLayout()
    icon_label = QtWidgets.QLabel()
    icon_label.setPixmap(QtGui.QPixmap(r"C:\OneDrive\Documents\4_PhD\10_PPT\template\UTokyoLab.resource\Picture1.png").scaled(128, 128, QtCore.Qt.KeepAspectRatio))  # 替换为你的 logo 路径
    top_layout.addWidget(icon_label)

    from . import __version__

    title_layout = QtWidgets.QVBoxLayout()
    title_label = QtWidgets.QLabel("Easy Agisoft MetaShape Plugin")
    title_label.setFont(QtGui.QFont("Arial", 14, QtGui.QFont.Bold))
    version_label = QtWidgets.QLabel(f"Version {__version__}")
    description_label = QtWidgets.QLabel("Extend Agisoft MetaShape for smart agriculture.")

    title_layout.addWidget(title_label)
    title_layout.addWidget(version_label)
    title_layout.addWidget(description_label)
    top_layout.addLayout(title_layout)

    layout.addLayout(top_layout)

    # 添加中间的文本框
    text_edit = QtWidgets.QTextEdit()
    text_edit.setReadOnly(True)
    text_edit.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded) 
    text_edit.setText(
        "Portions of this software are based in part on the work of the Independent JPEG Group.\n"
        "This software contains source code provided by NVIDIA Corporation.\n"
        "Some of the icons used are from the famfamfam silk (www.famfamfam.com) and FatCow (www.fatcow.com/free-icons/) icon sets.\n"
        "This software uses Qt and PySide libraries licensed under the GNU Lesser General Public Library version 3.\n"
        "Warning: This computer program is protected by copyright law and international treaties. Unauthorized reproduction or distribution of this program, or any portion of it, may result in severe civil and criminal penalties, and will be prosecuted to the maximum extent possible under the law."
    )
    layout.addWidget(text_edit)

    # 添加底部版权信息和按钮
    bottom_layout = QtWidgets.QHBoxLayout()
    copyright_label = QtWidgets.QLabel()
    copyright_label.setText(
        'Copyright (C) 2025 FieldPhenomics Lab, The University of Tokyo. <br>'
        '<a href="https://lab.fieldphenomics.com/">https://lab.fieldphenomics.com/</a>'
    )
    copyright_label.setOpenExternalLinks(True)  # 允许打开外部链接
    bottom_layout.addWidget(copyright_label)

    ok_button = QtWidgets.QPushButton("OK")
    ok_button.clicked.connect(dialog.accept)
    bottom_layout.addWidget(ok_button, alignment=QtCore.Qt.AlignRight)

    layout.addLayout(bottom_layout)

    # 显示对话框
    dialog.exec_()


class ProgressDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Detecting Stag Markers")
        self.resize(500, 120)
        self.setModal(True)  # 设置为模态对话框

        # 总进度条
        self.total_progress_label = QtWidgets.QLabel("Total Progress:")
        self.total_progress_bar = QtWidgets.QProgressBar()
        self.total_progress_bar.setRange(0, 100)

        # 分进度条
        self.sub_progress_label = QtWidgets.QLabel("Sub Progress:")
        self.sub_progress_bar = QtWidgets.QProgressBar()
        self.sub_progress_bar.setRange(0, 100)

        # 取消按钮
        self.cancel_btn = QtWidgets.QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)

        # 布局
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.total_progress_label)
        layout.addWidget(self.total_progress_bar)
        layout.addWidget(self.sub_progress_label)
        layout.addWidget(self.sub_progress_bar)
        layout.addWidget(self.cancel_btn)
        self.setLayout(layout)

    def update_total_progress(self, value):
        self.total_progress_bar.setValue(value)
        Metashape.app.update()

    def update_sub_progress(self, value):
        self.sub_progress_bar.setValue(value)
        Metashape.app.update()