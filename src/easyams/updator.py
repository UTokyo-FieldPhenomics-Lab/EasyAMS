import os
import requests
from packaging.version import Version

from PySide2.QtWidgets import (
    QApplication, QDialog, QLabel, QPushButton, QVBoxLayout, QHBoxLayout
)

from .utils import mprint, execude_command

installer_github_url = 'https://raw.githubusercontent.com/UTokyo-FieldPhenomics-Lab/EasyAMS/refs/heads/main/tools/installer.py'


def check_updates():
    installer_local_version = Version( get_installer_local_version() )
    installer_git_version   = Version( get_installer_git_version()   )
    package_local_version   = Version( get_package_local_version()   )
    package_pypi_version    = Version( get_package_pypi_version()    )

    installer_need_update = False
    if installer_git_version > installer_local_version:
        installer_need_update = installer_git_version

    package_need_update = False
    if package_pypi_version > package_local_version:
        package_need_update = self.package_pypi_version

    return installer_need_update, package_need_update, installer_local_version, package_local_version

class UpdateDialog(QDialog):

    def __init__(self, parent=None):

        super().__init__(parent)
        self.setWindowTitle("Check EasyAMS Updates")
        self.setFixedSize(300, 150)

        # Get versions
        # if no need updates, installer_need_update -> False, package_need_update -> False
        # if need updates,  installer_need_update -> Version(), package_need_update -> Version()
        self.installer_need_update, self.package_need_update, \
        self.installer_local_version, self.package_local_version = check_updates()

        self.create_ui()

    def create_ui(self):
        # Create widgets
        installer_local_version = QLabel(f"Installer version: {self.installer_local_version}")
        package_local_version = QLabel(f"Package version: {self.package_local_version}")
        info_label = QLabel(
            'You are using the latest version of EasyAMS'
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
        layout.addWidget(installer_local_version)
        layout.addWidget(package_local_version)
        layout.addWidget(info_label)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        # -> dependent on the updates condition.

        # judge the version and create the UI
        if self.installer_need_update:
            installer_update_text = f"A new installer version ({self.installer_need_update}) is available."
        else:
            installer_update_text = ""
        
        if self.package_need_update:
            package_update_text = f"A new package version ({self.package_pypi_version}) is available."
        else:
            package_update_text = ""

        ################
        # need updates #
        ################
        if self.installer_need_update or self.package_need_update:
            info_label.setText(f"{installer_update_text}\n{package_update_text}")

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
        if self.installer_need_update:
            self.update_installer()

        if self.package_need_update:
            self.update_package()

        super().accept()

    def reject(self):
        super().reject()

    def update_installer():
        local_installer_file = os.path.join(system_info.metashape_user_script_folder, 'easyams_launcher.py')

        response = requests.get(installer_github_url)
        if response.status_code == 200:
            with open(local_installer_file, 'w') as f:
                f.write(response.text)
            mprint("Installer updated successfully.")
            return True
        else:
            mprint(f"Failed to download installer. Status code: {response.status_code}")
            return False

    def update_package():
        from . import system_info
        self.config_manager = system_info.config_manager

        is_dev = self.config_manager.get('is_dev')
        if is_dev:
            Metashape.app.messageBox("Can not update editable package when installed in dev mode, please use git to update your source code folder")
            return False
        else:
            cmd = [
                system_info.easyams_uv,
                "pip",
                "install",
                "-U",
                "easyams"
            ]

            is_okay = execude_command(cmd, workdir=self.easyams_venv_folder)
            if is_okay:
                mprint("[EasyAMS] Packages updated successfully via uv.")
                return True
            else:
                mprint("[EasyAMS] Failed update dependencies via uv.")
                return False


def get_installer_local_version():
    from . import system_info

    local_installer_file = os.path.join(system_info.metashape_user_script_folder, 'easyams_launcher.py')

    if not os.path.exists(local_installer_file):
        mprint(f"[Error] Local installer file {local_installer_file} does not exist.")
        return None

    with open(local_installer_file, 'r') as f:
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