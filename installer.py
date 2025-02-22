import os
import sys
import platform
import shutil
import subprocess

import Metashape

def mprint(*values, **kwargs):
    print(*values, **kwargs)
    Metashape.app.update()

class Installer:

    def __init__(self):
        
        self.system = platform.system()

        self.metashape_user_script_folder = self.get_metashape_scripts_path()

        # current metashape buildin Python execuatable path
        self.metashape_python_executable_path = sys.executable

        # sys.version >>> '3.9.13 (main, Sep  9 2022, 11:31:02) \n[GCC 8.4.0]'
        self.metashape_python_version = sys.version.split(' ')[0] 

        # get current script path
        self.easyams_installer_folder = os.path.dirname(os.path.abspath(__file__))

        self.easyams_plugin_folder = os.path.join(self.metashape_user_script_folder, "EasyAMS")
        if not os.path.exists(self.easyams_plugin_folder):
            os.makedirs(self.easyams_plugin_folder)

        self.easyams_venv_folder = os.path.join(self.easyams_plugin_folder, "venv")

        # install status checker
        self.venv_is_ready = False
        self.dependencies_is_ready = False

    def get_metashape_scripts_path(self):

        home_dir = os.path.expanduser("~")

        if self.system == "Linux":
            script_path = os.path.join(home_dir, ".local", "share", "Agisoft", "Metashape Pro", "scripts")
        elif self.system == "Windows":
            script_path = os.path.join(home_dir, "AppData", "Local", "AgiSoft", "Metashape Pro", "scripts")
        elif self.system == "Darwin":  # macOS
            script_path = os.path.join(home_dir, "Library", "Application Support", "Agisoft", "Metashape Pro", "scripts")
        else:
            Metashape.app.messageBox("[EasyAMS] Unsupported operating system")
            raise OSError("[EasyAMS] Unsupported operating system")

        return script_path
    
    def check_campatibility(self):
        self.metashape_major_version = ".".join(Metashape.app.version.split('.')[:2])
    
    def print_paths(self):
        mprint(f"[EasyAMS] Platform: {self.system}")
        mprint(f"[EasyAMS] Metashape Buildin Python Executable Path: {self.metashape_python_executable_path}")
        mprint(f"[EasyAMS] User Plugin Script Path: {self.metashape_user_script_folder}")
        mprint(f"[EasyAMS] Current Installer Path: {self.easyams_installer_folder}")

    def execude_command(self, cmd):
        mprint(f"[EasyAMS][CMD] {' '.join(cmd)}")

        # sys.stdout.reconfigure(encoding='utf-8')
        # sys.stderr.reconfigure(encoding='utf-8')

        try:
            # 使用 Popen 执行命令
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8')

            # 实时读取标准输出
            for line in process.stdout:
                mprint(">>> ", line.strip())  # 打印每一行输出

            # 等待命令执行完成
            process.wait()

            # 检查是否有标准错误输出
            if process.returncode != 0:
                mprint("[EasyAMS][Error]:")
                for line in process.stderr:
                    mprint("   ", line.strip())
                    Metashape.app.update()

                return False
            else:
                return True

        except Exception as e:
            mprint(f"[EasyAMS][Error] when executing the following command:\n"
                    f"    {cmd}\n"
                    f"    {e}")
            return False

    def create_venv(self):
        mprint("[EasyAMS][Func] Creating virtual environment...")

        if self.system != "Windows":
            # not windows, just using `python -m venv <venv_folder>` to create venv
            install_uv_cmd = [
                self.metashape_python_executable_path,
                "-m",
                "venv",
                self.easyams_venv_folder
            ]

            # remove existing venv folder
            if os.path.exists(self.easyams_venv_folder):
                shutil.rmtree(self.easyams_venv_folder)


            is_okay = self.run_command(install_uv_cmd)
            if is_okay:
                mprint("[EasyAMS] virtual isolated python venv created")
            else:
                mprint("[EasyAMS] virtual isolated python venv creation failed")
            return is_okay
        else:
            # windows metashape build in python has bugs on creating venv, so we use uv instead
            install_uv_cmd = [
                self.metashape_python_executable_path,
                "-m",
                "pip",
                "install",
                "uv"
            ]

            is_okay = self.execude_command(install_uv_cmd)
            if is_okay:
                mprint("[EasyAMS] UV venv manager installed successfully.")
            else:
                mprint("[EasyAMS] Failed to install UV venv manager.")

            uv_executable_path = self.metashape_python_executable_path.replace("python.exe", "Scripts/uv.exe")
            
            # create venv using uv
            install_same_py_cmd = [
                uv_executable_path,
                "python",
                "install",
                self.metashape_python_version
            ]
            is_okay = self.execude_command(install_same_py_cmd)
            if is_okay:
                mprint("[EasyAMS] python with same version as Metashape installed successfully.")
            else:
                mprint("[EasyAMS] Failed to install python same version as Metashape.")

            # create venv using uv
            create_venv_cmd = [
                uv_executable_path,
                "venv",
                self.easyams_venv_folder.replace("\\", "/"),  # metashape path has spaces
                "--python",
                self.metashape_python_version
            ]
            is_okay = self.execude_command(create_venv_cmd)

            if is_okay:
                mprint("[EasyAMS] virtual isolated python venv created")
            else:
                mprint("[EasyAMS] virtual isolated python venv creation failed")

            return is_okay

    def venv_ready(self):
        if not os.path.exists(self.easyams_venv_folder):
            return self.venv_is_ready
        
        pyvenv_cfg_path = os.path.join(self.easyams_venv_folder, "pyvenv.cfg")
        if not os.path.exists(pyvenv_cfg_path):
            return self.venv_is_ready
        
        with open(pyvenv_cfg_path, "r") as f:
            content = f.readlines()
            for line in content:
                # 检查是否包含 Python 版本信息
                if line.startswith("version"):
                    self.easyams_venv_python_version = line.split("=")[1].strip()

        if self.easyams_venv_python_version == self.metashape_python_version:
            if self.system == "Windows":
                easyams_venv_python_executable_folder = os.path.join(self.easyams_venv_folder, "Scripts")
                self.easyams_venv_python_executable_file = os.path.join(easyams_venv_python_executable_folder, "python.exe")
            else:
                easyams_venv_python_executable_folder = os.path.join(self.easyams_venv_folder, "bin")
                self.easyams_venv_python_executable_file = os.path.join(easyams_venv_python_executable_folder, "python")
            
            self.check_pip_available( easyams_venv_python_executable_folder )

            self.venv_is_ready = True
            return self.venv_is_ready
        else:
            self.venv_is_ready = False
            Metashape.app.messageBox(
                f"[EasyAMS] venv python version ({self.easyams_venv_python_version}) "
                f"does not match with metashape python version {self.metashape_python_version}")
            return self.venv_is_ready
        
    def check_pip_available(self, pyexe_path):
        mprint(f'[EasyAMS][Func] Checking pip availability...')

        has_pip = False
        for exe in os.listdir(pyexe_path):
            if 'pip' in exe:
                has_pip = True
                break
        
        if not has_pip:
            # install pip from curl
            get_pip_py = os.path.join(self.easyams_plugin_folder, "get-pip.py")

            if not os.path.exists(get_pip_py):
                curl_cmd = [
                    "curl",
                    "--output", 
                    get_pip_py,
                    "https://bootstrap.pypa.io/get-pip.py"
                ]

                is_okay = self.execude_command(curl_cmd)
                if is_okay and os.path.exists(get_pip_py):
                    mprint(f'[EasyAMS][Func] get-pip.py downloaded successfully.')
                else:
                    mprint(f'[EasyAMS][Error] Failed to download get-pip.py')
            
            if os.path.exists(get_pip_py):
                install_pip_cmd = [
                    self.easyams_venv_python_executable_file,
                    get_pip_py
                ]
                is_okay = self.execude_command(install_pip_cmd)
                if is_okay:
                    mprint(f'[EasyAMS][Func] pip installed successfully.')
                else:
                    mprint(f'[EasyAMS][Error] Failed to install pip')
            
        
    def install_dependencies(self):
        mprint(f'[EasyAMS][Func] Installing dependencies...')

        # todo: need check if the dependencies are already installed

        if self.venv_is_ready or self.venv_ready():
            cmd = [
                self.easyams_venv_python_executable_file,
                "-m",
                "pip",
                "install",
                "numpy==1.26.4"
                # "-r",
                # f"{self.easyams_plugin_folder}"
            ]

            is_okay = self.execude_command(cmd)
            if is_okay:
                mprint("[EasyAMS] Dependencies installed successfully.")
            else:
                mprint("[EasyAMS] Failed to install dependencies.")

    def add_venv_to_path(self):
        mprint(f'[EasyAMS][Func] Adding virtual environment to PATH...')

        if self.venv_is_ready or self.venv_ready():

            if self.system == 'Windows':
                # Add the Scripts directory to PATH
                site_packages_folder  = os.path.join(self.easyams_venv_folder, "Lib", "site-packages")

            else:
                lib_path = os.path.join(self.easyams_venv_folder, "lib")

                # exclude the ".DS_Store" and other non-python folders
                lib_folders = [i for i in os.listdir(lib_path) if "python" in i]
                if len(lib_folders) == 1:
                    site_packages_folder = os.path.join(lib_path, lib_folders[0], "site-packages")
                else:
                    Metashape.app.messageBox(
                        f"[EasyAMS] Find multiple python libs {lib_folders} at venv folder '{lib_path}'"
                    )

            if os.path.exists(site_packages_folder):
                sys.path.insert(0, site_packages_folder)
            else:
                Metashape.app.messageBox(
                    f"[EasyAMS] venv missing site-package folders of '{site_packages_folder}'"
                )


def path_equal(path1, path2):
    abs_path1 = os.path.abspath(os.path.normpath(path1))
    abs_path2 = os.path.abspath(os.path.normpath(path2))
    return abs_path1 == abs_path2

def show_about_dialog():
    from PySide2 import QtWidgets, QtGui, QtCore

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
    env = Installer()

    if path_equal(env.easyams_installer_folder, env.metashape_user_script_folder):
        # the installer is installed correctly (inside the metashape script launcher folder)
        Metashape.app.addMenuItem("EasyAMS/StagMarkers/Detect Markers", env.print_paths)
        Metashape.app.addMenuItem("EasyAMS/StagMarkers/Print Markers", env.print_paths)
        Metashape.app.addMenuSeparator("EasyAMS")
        Metashape.app.addMenuItem("EasyAMS/Check for Updates", env.print_paths)
        Metashape.app.addMenuItem("EasyAMS/About EasyAMS", show_about_dialog)
    else:
        mprint("[EasyAMS] Installing the plugin...")

        # create virtual envs
        if not env.venv_ready():
            env.create_venv()

        if env.venv_is_ready or env.venv_ready():
            env.install_dependencies()

            env.add_venv_to_path()

        env.print_paths()