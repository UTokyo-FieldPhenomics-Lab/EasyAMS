import os
import requests
from packaging.version import Version
from dataclasses import dataclass
from typing import Optional

from PySide2.QtWidgets import (
    QApplication, QDialog, QLabel, QPushButton, QVBoxLayout, QHBoxLayout
)

import Metashape

from .utils import mprint, execude_command

installer_github_url = 'https://raw.githubusercontent.com/UTokyo-FieldPhenomics-Lab/EasyAMS/refs/heads/main/tools/installer.py'

@dataclass
class VersionInfo:
    outdated: bool
    local: str
    latest: str

@dataclass
class VersionData:
    installer: VersionInfo
    package: VersionInfo
    onnx: VersionInfo

def check_updates():
    installer_local_version = Version( get_installer_local_version() )
    installer_github_version   = Version( get_installer_git_version()   )
    installer_need_update = False
    if installer_github_version > installer_local_version:
        installer_need_update = True

    package_local_version   = Version( get_package_local_version()   )
    package_pypi_version    = Version( get_package_pypi_version()    )

    package_need_update = False
    if package_pypi_version > package_local_version:
        package_need_update = True

    from . import system_info
    onnx_need_update, onnx_local_version, onnx_github_version = system_info.onnx.outdated(return_versions=True)

    ver = VersionData(
        installer=VersionInfo(
            outdated=installer_need_update,
            local=installer_local_version,
            latest=installer_github_version
        ),
        package=VersionInfo(
            outdated=package_need_update,
            local=package_local_version,
            latest=package_pypi_version
        ),
        onnx=VersionInfo(
            outdated=onnx_need_update,
            local=onnx_local_version,
            latest=onnx_github_version
        )
    )

    has_updates = ver.installer.outdated or ver.package.outdated or ver.onnx.outdated

    return ver, has_updates


class UpdateDialog(QDialog):

    def __init__(self, parent=None):

        super().__init__(parent)
        self.setWindowTitle("Check EasyAMS Updates")
        self.setMinimumSize(300, 150)

        from . import system_info
        self.system_info = system_info

        # Get versions
        self.ver, self.has_updates = check_updates()

        self.create_ui()

    def create_ui(self):
        # Create widgets
        installer_version = QLabel(f"Installer version: {self.ver.installer.local}" + 
            ( f" (latest: {self.ver.installer.latest} available)" if self.ver.installer.outdated else "" ) 
        )
        package_version   = QLabel(f"Package version: {self.ver.package.local}" + 
            ( f" (latest: {self.ver.package.latest} available)" if self.ver.package.outdated else "")
        )
        onnx_version      = QLabel(f"Yolo onnx model version: {self.ver.onnx.local}" + 
           ( f" (latest: {self.ver.onnx.latest} available)" if self.ver.onnx.outdated else "")
        )

        info_label = QLabel(
            'You are using the latest version of EasyAMS' if not self.has_updates else 'Updates available.'
        )
        update_button = QPushButton("Update")
        ok_btn = QPushButton("OK")
        cancel_btn = QPushButton("Cancel")

        # Connect the OK button
        update_button.clicked.connect(self.accept)
        ok_btn.clicked.connect(self.reject)
        cancel_btn.clicked.connect(self.reject)

        # Setup the layout
        layout = QVBoxLayout()
        layout.addWidget(installer_version)
        layout.addWidget(package_version)
        layout.addWidget(onnx_version)
        layout.addWidget(info_label)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        # -> dependent on the updates condition.
        ################
        # need updates #
        ################
        if self.ver.installer.outdated or self.ver.package.outdated or self.ver.onnx.outdated:
            button_layout.addWidget(update_button)
            button_layout.addWidget(cancel_btn)
            layout.addLayout(button_layout)

        ###################
        # no need updates #
        ###################
        else:
            button_layout.addWidget(ok_btn)
            layout.addLayout(button_layout)
        
        self.setLayout(layout)

        self.show()

    def accept(self):
        if self.ver.installer.outdated:
            installer_success = self.update_installer()
        else:
            installer_success = True

        if self.ver.package.outdated:
            package_success = self.update_package()
        else:
            package_success = True

        if self.ver.onnx.outdated:
            onnx_success = self.system_info.onnx.update()
        else:
            onnx_success = True

        if installer_success and package_success and onnx_success:
            Metashape.app.messageBox("Updated successfully")

        super().accept()

    def reject(self):
        super().reject()

    def update_installer(self):
        local_installer_file = os.path.join(self.system_info.metashape_user_script_folder, 'easyams_launcher.py')

        response = requests.get(installer_github_url)
        if response.status_code == 200:
            with open(local_installer_file, 'w') as f:
                f.write(response.text)
            mprint("Installer updated successfully.")
            return True
        else:
            mprint(f"Failed to download installer. Status code: {response.status_code}")
            Metashape.app.messageBox("Installer automatic update failed. Please manually download `EasyAMS/tools/installer.py` file and reinstall again via Metashape scripts.")
            return False

    def update_package(self):
        is_dev = self.system_info.config_manager.load('is_dev')
        if is_dev:
            Metashape.app.messageBox("Can not update editable package when installed in dev mode, please use git to update your source code folder")
            return False
        else:
            cmd = [
                self.system_info.easyams_uv,
                "pip",
                "install",
                "-U",
                "easyams"
            ]

            is_okay = execude_command(cmd, workdir=self.system_info.easyams_venv_folder)
            if is_okay:
                mprint("[EasyAMS] Packages updated successfully via uv.")
                return True
            else:
                mprint("[EasyAMS] Failed update dependencies via uv.")
                Metashape.app.messageBox("Package automatic update failed via uv. Please check your network connections or report an issue to EasyAMS.")
                return False


def get_installer_local_version():
    from . import system_info

    local_installer_file = os.path.join(system_info.metashape_user_script_folder, 'easyams_launcher.py')

    if not os.path.exists(local_installer_file):
        mprint(f"[Error] Local installer file {local_installer_file} does not exist.")
        return None

    with open(local_installer_file, 'r', encoding="utf-8") as f:
        lines = f.readlines()

        # Find the line containing __version__
        version_line = None
        for i, line in enumerate(lines):
            if '__version__' in line:
                version_line = line
                break

        if version_line:
            # Extract the version string
            version = version_line.split('=')[1].strip().strip('"')
            return version
        else:
            return f"Version not found in the local installer file [{local_installer_file}]."

def get_installer_git_version():
    try:
        response = requests.get( installer_github_url )
        response.raise_for_status()

        # Find the line containing __version__
        version_line = None
        for line in response.text.split('\n'):
            if '__version__' in line:
                version_line = line
                break

        if version_line:
            # Extract the version string
            version = version_line.split('=')[1].strip().strip('"')
            return version
        else:
            return "Version not found in the github repository."
    except requests.RequestException as e:
        return f"Failed to fetch version: {str(e)}"


def get_package_pypi_version():
    try:
        response = requests.get('https://pypi.org/pypi/easyams/json')
        response.raise_for_status()
        # Extract the version string from the JSON response
        data = response.json()
        return data['info']['version']
    except requests.RequestException as e:
        return f"Failed to fetch version: {str(e)}"

def get_package_local_version():
    from . import __version__
    return __version__

def check_updates_ui():
    app = QApplication.instance()  # 获取当前Qt应用实例
    window = UpdateDialog(app.activeWindow())
    window.exec_()  # 使用exec_()而非show()确保模态性