import os
import re
import sys
import platform
import shutil
import hashlib
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

def path_equal(path1, path2):
    abs_path1 = os.path.abspath(os.path.normpath(path1))
    abs_path2 = os.path.abspath(os.path.normpath(path2))
    return abs_path1 == abs_path2

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

        self.easyams_plugin_folder = os.path.abspath(
            os.path.join(
                self.metashape_user_script_folder, 
                f"../easyams-packages-py{sys.version_info.major}{sys.version_info.minor}"))
        
        if not os.path.exists(self.easyams_plugin_folder):
            os.makedirs(self.easyams_plugin_folder)

        self.easyams_venv_folder = os.path.join(self.easyams_plugin_folder, "venv")

        # install status checker
        self.venv_is_ready = False

        self.required_packages = self.parse_requirements(REQUIREMENTS_INFERENCE)
        self.installed_packages = {}   # {'package': version, ...}
        self.not_installed_packages = []  # 'package==version' for pip command
        self.package_is_ready = False

        # git downloader
        self.gitdown = GitReleaseDownloader(
            repo="UTokyo-FieldPhenomics-Lab/EasyAMS",  # 替换为实际的 GitHub 仓库路径
            save_path=self.easyams_plugin_folder,  # 替换为实际的保存路径
            file_name="yolo11_stag",  # 文件基础名称
            suffix="onnx",  # 文件后缀
            # token="your_github_token"  # 可选：GitHub 个人访问令牌
        )

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

                # link editable easyams folder for dev
                for item in os.listdir(site_packages_folder):
                    if item.endswith('.egg-link'):
                        with open(os.path.join(site_packages_folder, item), 'r') as f:
                            # .egg-link 文件的第一行是包的路径
                            package_path = f.readline().strip()
                            if os.path.exists(package_path):
                                sys.path.insert(0, package_path)
            else:
                Metashape.app.messageBox(
                    f"[EasyAMS] venv missing site-package folders of '{site_packages_folder}'"
                )

    def check_onnx_version(self):
        # 检查是否需要更新
        is_outdated, local_version, github_version = self.gitdown.outdated(return_versions=True)
        if is_outdated:
            print(f"[EasyAMS] Local YOLO.onnx file version v{local_version} is outdated, the latested Github release version v{github_version} is available.")
            latest_version = self.gitdown.update()
        else:
            print(f"[EasyAMS] Local YOLO.onnx file version v{local_version} is up-to-date.")

    
    def get_onnx_file(self):
        latest_version = self.gitdown.local_version()

        return os.path.join(self.easyams_plugin_folder, f"yolo11_stag_v{latest_version}.onnx")


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

            global requests
            import requests
            self.check_onnx_version()


class GitReleaseDownloader:

    def __init__(self, repo: str, save_path: str, file_name: str, suffix: str, token: str = None):
        """
        初始化 GitReleaseDownloader 实例
        :param repo: GitHub 仓库路径，格式为 "org/repo"
        :param save_path: 本地保存文件的路径
        :param file_name: 文件的基础名称（不包含版本号和后缀）
        :param suffix: 文件后缀（如 "onnx"）
        :param token: 可选，GitHub 个人访问令牌，用于认证
        """
        self.repo = repo
        self.save_path = save_path
        self.file_name = file_name
        self.suffix = suffix
        self.token = token
        self.headers = {"Authorization": f"token {token}"} if token else {}

        # 确保保存路径存在
        if not os.path.exists(save_path):
            os.makedirs(save_path, exist_ok=True)

    def local_version(self) -> int:
        """
        获取本地文件的版本号
        :return: 本地文件的版本号（整数），如果不存在则返回 0
        """
        pattern = re.compile(rf"{self.file_name}_v(\d+)\.{self.suffix}")
        files = os.listdir(self.save_path)
        for file in files:
            match = pattern.match(file)
            if match:
                return int(match.group(1))
        return 0

    def git_release_version(self) -> int:
        """
        获取 GitHub Releases 中最新文件的版本号
        :return: 最新文件的版本号（整数）
        """
        url = f"https://api.github.com/repos/{self.repo}/releases/latest"
        response = requests.get(url, headers=self.headers)
        if response.status_code != 200:
            raise Exception(f"Failed to fetch latest release: {response.status_code}, {response.text}")

        release_data = response.json()
        assets = release_data.get("assets", [])
        pattern = re.compile(rf"{self.file_name}_v(\d+)\.{self.suffix}")
        for asset in assets:
            match = pattern.match(asset["name"])
            if match:
                return int(match.group(1))
        raise Exception(f"No matching file found in the latest release for pattern: {self.file_name}_v?.{self.suffix}")

    def outdated(self, return_versions=False) -> bool:
        """
        检查本地文件是否过期
        :return: 如果本地文件版本低于 GitHub 最新版本，则返回 True，否则返回 False
        """
        local_version = self.local_version()
        github_version = self.git_release_version()

        is_outdated = github_version > local_version

        if return_versions:
            return is_outdated, local_version, github_version
        else:
            return is_outdated

    def update(self):
        """
        更新本地文件到最新版本
        :raises: 如果下载失败或文件校验失败，则抛出异常
        """
        # 获取最新版本号和下载链接
        url = f"https://api.github.com/repos/{self.repo}/releases/latest"
        response = requests.get(url, headers=self.headers)
        if response.status_code != 200:
            raise Exception(f"Failed to fetch latest release: {response.status_code}, {response.text}")

        release_data = response.json()
        assets = release_data.get("assets", [])
        pattern = re.compile(rf"{self.file_name}_v(\d+)\.{self.suffix}")
        download_url = None
        latest_version = None
        sha256_url = None

        for asset in assets:
            match = pattern.match(asset["name"])
            if match:
                latest_version = int(match.group(1))
                if "sha256" not in asset["name"]:
                    download_url = asset["browser_download_url"]
            # 查找 SHA256 校验文件
            if asset["name"] == f"{self.file_name}_v{latest_version}.sha256":
                sha256_url = asset["browser_download_url"]

        if not download_url or latest_version is None:
            raise Exception(f"No matching file found in the latest release for pattern: {self.file_name}_v?.{self.suffix}")

        # 下载文件
        local_file_path = os.path.join(self.save_path, f"{self.file_name}_v{latest_version}.{self.suffix}")
        print(f"Downloading {download_url} to {local_file_path} ...")
        with requests.get(download_url, headers=self.headers, stream=True) as r:
            if r.status_code != 200:
                raise Exception(f"Failed to download file: {r.status_code}, {r.text}")
            with open(local_file_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)

        # 下载并校验 SHA256
        print("Verifying file integrity using SHA256...")
        sha256_hash = self._download_sha256(assets, f"{self.file_name}_v{latest_version}.{self.suffix}")
        if not self._verify_file_sha256(local_file_path, sha256_hash):
            os.remove(local_file_path)  # 删除下载的无效文件
            raise Exception("SHA256 verification failed. The downloaded file is corrupted or tampered.")
        
        # 删除旧文件
        self._delete_old_files(latest_version)
        print(f"[EasyAMS] Update complete. Latest version: v{latest_version}")

        return latest_version

    def _delete_old_files(self, latest_version: int):
        """
        删除旧版本的文件
        :param latest_version: 最新版本号
        """
        pattern = re.compile(rf"{self.file_name}_v(\d+)\.{self.suffix}")
        files = os.listdir(self.save_path)
        for file in files:
            match = pattern.match(file)
            if match:
                version = int(match.group(1))
                if version < latest_version:
                    old_file_path = os.path.join(self.save_path, file)
                    os.remove(old_file_path)
                    print(f"Deleted old file: {old_file_path}")

    def _download_sha256(self, assets, target_file_name: str) -> str:
        """
        下载与目标文件同名的 .sha256 文件，并提取 SHA256 校验值
        :param assets: GitHub Release 的 assets 列表
        :param target_file_name: 目标文件的名称（如 yolov11_stag_v1.onnx）
        :return: SHA256 校验值
        """
        sha256_file_name = f"{target_file_name}.sha256"
        for asset in assets:
            if asset["name"] == sha256_file_name:
                sha256_url = asset["browser_download_url"]
                response = requests.get(sha256_url, headers=self.headers)
                if response.status_code != 200:
                    raise Exception(f"Failed to download SHA256 file: {response.status_code}, {response.text}")
                return response.text.strip()
        raise Exception(f"SHA256 file not found for {target_file_name}")

    def _verify_file_sha256(self, file_path: str, sha256_hash: str) -> bool:
        """
        校验文件的 SHA256 值
        :param file_path: 文件路径
        :param sha256_hash: 预期的 SHA256 值
        :return: 如果校验通过返回 True，否则返回 False
        """
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)
        calculated_hash = sha256.hexdigest()
        return calculated_hash == sha256_hash
        

if __name__ == "__main__":
    installer = Installer()

    if path_equal(installer.easyams_installer_folder, installer.metashape_user_script_folder):
        # the installer is installed correctly (inside the metashape script launcher folder)
        installer.add_venv_to_path()
        
        import easyams as ams

        Metashape.app.addMenuItem("EasyAMS/Import Videos", ams.video_split.start_video_extractor)

        Metashape.app.addMenuItem("EasyAMS/StagMarkers/Detect Markers", ams.stag_gcp.detect_stag_markers)
        Metashape.app.addMenuItem("EasyAMS/StagMarkers/Print Markers", installer.print_paths)
        Metashape.app.addMenuSeparator("EasyAMS")
        Metashape.app.addMenuItem("EasyAMS/Check for Updates", installer.print_paths)
        Metashape.app.addMenuItem("EasyAMS/About EasyAMS", ams.ui.show_about_dialog)
    else:
        installer.main()
        installer.print_paths()