import os
import sys
import platform
import shutil
import subprocess

from packaging import version

import Metashape

REQUIREMENTS_INFERENCE = """
# opencv numpy requirements
numpy==1.26.4

# stag
stag-python==1.1.0
opencv-python==4.10.0.84

# inference
onnx==1.17.0
onnxruntime==1.19.2

# modified sahi package for inferencing, thus no need ultralytics, torch framework for inferencing
# sahi==0.11.20
# ultralytics==8.3.77
# torch==2.5.1
# torchvision==0.20.1
shapely>=2.0.0
tqdm>=4.48.2
pillow>=8.2.0
pybboxes==0.1.6
requests==2.32.3
"""

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

        self.required_packages = self.parse_requirements(REQUIREMENTS_INFERENCE)
        self.installed_packages = {}   # {'package': version, ...}
        self.not_installed_packages = []  # 'package==version' for pip command
        self.package_is_ready = False

    def get_metashape_scripts_path(self):

        home_dir = os.path.expanduser("~")

        if self.system == "Linux":
            script_path = os.path.join(home_dir, ".local", "share", "Agisoft", "Metashape Pro", "scripts")
        elif self.system == "Windows":
            script_path = os.path.join(home_dir, "AppData", "Local", "Agisoft", "Metashape Pro", "scripts")
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
        
    @staticmethod
    def uv_installed_in_ms_python():
        import pkg_resources
        try:
            # Parse the dependency (e.g., "numpy==1.26.4" or "shapely>=2.0.0")
            # Check if the installed version satisfies the requirement
            pkg_resources.require('uv')
            print(f"[EasyAMS] uv is installed in Metashape buildin python.")
            return True
        except pkg_resources.DistributionNotFound:
            print(f"[EasyAMS] uv is not installed in Metashape buildin python.")
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


            is_okay = self.execude_command(install_uv_cmd)
            if is_okay:
                mprint("[EasyAMS] virtual isolated python venv created")
            else:
                mprint("[EasyAMS] virtual isolated python venv creation failed")
            return is_okay
        else:
            # windows metashape build in python has bugs on creating venv, so we use uv instead
            if not self.uv_installed_in_ms_python():

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
                    return False

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

    # 提取非注释的依赖项
    @staticmethod
    def parse_requirements(requirements_str):
        dependencies = []
        for line in requirements_str.splitlines():
            line = line.strip()
            # 忽略空行和注释行
            if line and not line.startswith("#"):
                dependencies.append(line)
        return dependencies
    
    def get_venv_installed_package_info(self):
        """
        Get a dictionary of installed packages and their versions in the specified virtual environment.

        :param venv_python_path: The path to the Python executable in the virtual environment.
        :return: A dictionary where keys are package names and values are their installed versions.
        """
        try:
            # Use `pip list` to get all installed packages and their versions
            result = subprocess.run(
                [
                    self.easyams_venv_python_executable_file, 
                    "-m", "pip", "list", "--format=freeze"
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            if result.returncode != 0:
                raise RuntimeError(f"[EasyAMS] Failed to get installed packages: {result.stderr}")

            # Parse the output of `pip list`
            self.installed_packages = {}
            for line in result.stdout.splitlines():
                if "==" in line:  # Only consider lines with "package==version"
                    package, version = line.split("==")
                    self.installed_packages[package.lower()] = version
        except Exception as e:
            mprint(f"[EasyAMS] Error while getting installed packages: {e}")
            self.installed_packages = {}

    # Check if a dependency is installed with the correct version
    def check_one_package_in_venv(self, dependency):
        """
        Check if a dependency is installed and meets the required version.

        :param dependency: The dependency string (e.g., "numpy==1.26.4" or "shapely>=2.0.0").
        :param installed_packages: A dictionary of installed packages and their versions.
        :return: True if the dependency is installed and meets the required version, False otherwise.
        """

        try:
            # Parse the dependency (e.g., "numpy==1.26.4" or "shapely>=2.0.0")
            # only == and >= are supported in EasyAMS requirements.txt
            if "==" in dependency:
                package, required_version = dependency.split("==")
                package = package.lower()
                if package in self.installed_packages.keys():
                    installed_version = self.installed_packages[package]
                    if version.parse(installed_version) == version.parse(required_version):
                        mprint(f">>> {dependency} is installed and meets the required version.")
                        return True
                    else:
                        mprint(f">>> {dependency} is installed, but the version is {installed_version} (required: {required_version}).")
                        return False
                else:
                    mprint(f">>> {dependency} is not installed.")
                    return False
            elif ">=" in dependency:
                package, required_version = dependency.split(">=")
                package = package.lower()
                if package in self.installed_packages:
                    installed_version = self.installed_packages[package]
                    if version.parse(installed_version) >= version.parse(required_version):
                        mprint(f">>> {dependency} is installed and meets the required version.")
                        return True
                    else:
                        mprint(f">>> {dependency} is installed, but the version is {installed_version} (required: >= {required_version}).")
                        return False
                else:
                    mprint(f">>> {dependency} is not installed.")
                    return False
            else:
                package = dependency.lower()
                if package in self.installed_packages.keys():
                    mprint(f">>> {dependency} is installed (no specific version requirement).")
                    return True
                else:
                    mprint(f">>> {dependency} is not installed.")
                    return False
        except Exception as e:
            mprint(f"[EasyAMS][func] Error checking dependency {dependency}: {e}")
            return False
        
    def check_dependencies(self):
        self.get_venv_installed_package_info()

        for dependency in self.required_packages:
            if not self.check_one_package_in_venv(dependency):
                self.not_installed_packages.append(dependency)

        if len(self.not_installed_packages) > 0:
            self.package_is_ready = False
            mprint(f"[EasyAMS][Func] Dependencies not satisfied")
            return False
        else:
            self.package_is_ready = True
            mprint(f"[EasyAMS][Func] Dependencies satisfied")
            return True
        
    def install_dependencies(self):
        mprint(f'[EasyAMS][Func] Installing dependencies...')

        if self.venv_is_ready or self.venv_ready():
            Metashape.app.messageBox("During EasyAMS installation, the Metashape UI may stuck for a while, please wait patiently until finished.")

            cmd = [
                self.easyams_venv_python_executable_file,
                "-m",
                "pip",
                "install",
                *self.not_installed_packages
            ]

            is_okay = self.execude_command(cmd)
            if is_okay:
                mprint("[EasyAMS] Dependencies installed successfully.")
                Metashape.app.messageBox("EasyAMS dependencies successfully installed.")
            else:
                mprint("[EasyAMS] Failed to install dependencies.")

    def _install_easyams_dev(self):

        if self.venv_is_ready or self.venv_ready():

            cmd = [
                self.easyams_venv_python_executable_file,
                "-m",
                "pip",
                "install",
                "-e",
                self.easyams_installer_folder
            ]

            is_okay = self.execude_command(cmd)
            if is_okay:
                mprint("[EasyAMS] EasyAMS package installed successfully.")
                Metashape.app.messageBox("EasyAMS successfully installed.")
            else:
                mprint("[EasyAMS] Failed to install EasyAMS package.")

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

    def main(self):
        mprint("[EasyAMS] Initializing the plugin...")
        # create virtual envs
        if not self.venv_ready():
            self.create_venv()

        if self.venv_is_ready or self.venv_ready():
            if not self.check_dependencies():
                self.install_dependencies()

            if not self.check_one_package_in_venv('easyams'):
                self._install_easyams_dev()

            self.add_venv_to_path()


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
    installer = Installer()

    if path_equal(installer.easyams_installer_folder, installer.metashape_user_script_folder):
        # the installer is installed correctly (inside the metashape script launcher folder)
        Metashape.app.addMenuItem("EasyAMS/StagMarkers/Detect Markers", installer.print_paths)
        Metashape.app.addMenuItem("EasyAMS/StagMarkers/Print Markers", installer.print_paths)
        Metashape.app.addMenuSeparator("EasyAMS")
        Metashape.app.addMenuItem("EasyAMS/Check for Updates", installer.print_paths)
        Metashape.app.addMenuItem("EasyAMS/About EasyAMS", show_about_dialog)
    else:
        installer.main()
        installer.print_paths()