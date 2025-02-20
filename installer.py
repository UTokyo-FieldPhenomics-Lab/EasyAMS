import os
import sys
import platform

import Metashape
from PySide2 import QtWidgets, QtGui, QtCore

class Installer:

    def __init__(self):
        
        self.system = platform.system()

        self.user_script_path = self.get_metashape_scripts_path()

        # current metashape buildin Python execuatable path
        self.ms_python_executable_path = sys.executable

        # get current script path
        self.installer_script_folder = os.path.dirname(os.path.abspath(__file__))

    def get_metashape_scripts_path(self):

        home_dir = os.path.expanduser("~")

        if self.system == "Linux":
            path = os.path.join(home_dir, ".local", "share", "Agisoft", "Metashape Pro", "scripts")
        elif self.system == "Windows":
            path = os.path.join(home_dir, "AppData", "Local", "AgiSoft", "Metashape Pro", "scripts")
        elif self.system == "Darwin":  # macOS
            path = os.path.join(home_dir, "Library", "Application Support", "Agisoft", "Metashape Pro", "scripts")
        else:
            raise OSError("Unsupported operating system")

        return path
    
    def print_paths(self):
        print(f"[EasyAMS] Platform: {self.system}")
        print(f"[EasyAMS] Metashape Buildin Python Executable Path: {self.ms_python_executable_path}")
        print(f"[EasyAMS] User Plugin Script Path: {self.user_script_path}")
        print(f"[EasyAMS] Current Installer Path: {self.installer_script_folder}")

def path_equal(path1, path2):
    # 获取路径的绝对规范化形式
    abs_path1 = os.path.abspath(os.path.normpath(path1))
    abs_path2 = os.path.abspath(os.path.normpath(path2))
    return abs_path1 == abs_path2

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

    title_layout = QtWidgets.QVBoxLayout()
    title_label = QtWidgets.QLabel("Easy Agisoft MetaShape Plugin")
    title_label.setFont(QtGui.QFont("Arial", 14, QtGui.QFont.Bold))
    version_label = QtWidgets.QLabel("Version 0.0.1")
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

if __name__ == "__main__":
    inst = Installer()

    if path_equal(inst.installer_script_folder, inst.user_script_path):
        # the installer is inside the metashape script launcher folder, functions installed correctly.
        Metashape.app.addMenuItem("EasyAMS/StagMarkers/Detect Markers", inst.print_paths)
        Metashape.app.addMenuItem("EasyAMS/StagMarkers/Print Markers", inst.print_paths)
        Metashape.app.addMenuSeparator("EasyAMS")
        Metashape.app.addMenuItem("EasyAMS/Check for Updates", inst.print_paths)
        Metashape.app.addMenuItem("EasyAMS/About EasyAMS", show_about_dialog)
    else:
        print("[EasyAMS] Installing the plugin...")
        inst.print_paths()