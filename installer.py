import os
import re
import sys
import platform
import shutil
import hashlib
import subprocess

# uv installer dependencies
import tempfile
import tarfile
import zipfile
from typing import Dict, Optional

import Metashape

def mprint(*values, **kwargs):
    prefixed_values = ["[EasyAMS]"] + list(values)
    print(*prefixed_values, **kwargs)
    Metashape.app.update()

def path_equal(path1, path2):
    abs_path1 = os.path.abspath(os.path.normpath(path1))
    abs_path2 = os.path.abspath(os.path.normpath(path2))
    return abs_path1 == abs_path2

def execude_command(cmd):
    mprint(f"[CMD] {' '.join(cmd)}")

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
            mprint("[Error]:")
            for line in process.stderr:
                mprint("   ", line.strip())
                Metashape.app.update()

            return False
        else:
            return True

    except Exception as e:
        mprint(f"[Error] when executing the following command:\n"
               f"    {cmd}\n"
               f"    {e}")
        return False


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

        self.easyams_venv_folder = os.path.join(self.easyams_plugin_folder, ".venv")
        self.easyams_bin_folder = os.path.join(self.easyams_plugin_folder, "bin")

        self.easyams_uv = os.path.join(self.easyams_bin_folder, "uv.exe" if self.system == "Windows" else "uv")

        # install status checker
        self.venv_is_ready = False
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

        
    def is_uv_installed(self) -> str:
        """
        Returns
        -------
        str
            The commend to execute uv
        """

        # test if uv is globally installed on the system
        if shutil.which("uv") is not None:
            mprint(f"uv is detected on this PC")
            self.easyams_uv = "uv"
            return True
        else:
            # use 3rd party uv just for easyams package
            if os.path.exists( self.easyams_uv ):
                return True
            else:
                # install uv bin to package folder
                installer = UvInstaller(install_dir=self.easyams_bin_folder)
                success = installer.install()
                if success:
                    return True
                else:
                    return False

    def create_venv(self):
        mprint("[EasyAMS][Func] Creating virtual environment...")

        # create venv using uv
        install_same_py_cmd = [
            self.easyams_uv, 
            "python",
            "install",
            self.metashape_python_version
        ]
        is_okay = execude_command(install_same_py_cmd)
        if is_okay:
            mprint("[EasyAMS] python with same version as Metashape installed successfully.")
        else:
            mprint("[EasyAMS] Failed to install python same version as Metashape.")

        # create venv using uv
        create_venv_cmd = [
            self.easyams_uv, 
            "venv",
            self.easyams_venv_folder.replace("\\", "/"),  # metashape path has spaces
            "--python",
            self.metashape_python_version
        ]
        is_okay = execude_command(create_venv_cmd)

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

            self.venv_is_ready = True
            return self.venv_is_ready
        else:
            self.venv_is_ready = False
            Metashape.app.messageBox(
                f"[EasyAMS] venv python version ({self.easyams_venv_python_version}) "
                f"does not match with metashape python version {self.metashape_python_version}")
            return self.venv_is_ready
        
    def check_dependencies(self):
        # self.get_venv_installed_package_info()

        # for dependency in self.required_packages:
        #     if not self.check_one_package_in_venv(dependency):
        #         self.not_installed_packages.append(dependency)

        # if len(self.not_installed_packages) > 0:
        #     self.package_is_ready = False
        #     mprint(f"[EasyAMS][Func] Dependencies not satisfied")
        #     return False
        # else:
        #     self.package_is_ready = True
        #     mprint(f"[EasyAMS][Func] Dependencies satisfied")
        #     return True

        cmd = [
            self.easyams_uv,
            '--version'
        ]

        is_okay = execude_command(cmd)
        
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

            is_okay = execude_command(cmd)
            if is_okay:
                mprint("[EasyAMS] Dependencies installed successfully.")
                Metashape.app.messageBox("EasyAMS dependencies successfully installed.")
            else:
                mprint("[EasyAMS] Failed to install dependencies.")

    def _install_easyams_dev(self):
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

    def check_onnx_file_version(self):
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

        if not self.is_uv_installed():
            raise FileNotFoundError("[EasyAMS] Can not find system uv or plugin bulit-in uv for setting up dependencies")

        # create virtual envs
        if not self.venv_ready():
            self.create_venv()

        if self.venv_is_ready or self.venv_ready():

            self.check_dependencies()
            # if not self.check_dependencies():
            #     self.install_dependencies()

            # if not self.check_one_package_in_venv('easyams'):
            #     self._install_easyams_dev()

            # self.add_venv_to_path()

            # global requests
            # import requests
            # self.check_onnx_file_version()


class UvInstaller:

    """A class to handle downloading and installing uv binaries. Inspiared by 
    https://github.com/CherryHQ/cherry-studio/blob/develop/resources/scripts/install-uv.js
    """

    # Base URL for downloading uv binaries
    UV_RELEASE_BASE_URL = "http://gitcode.com/CherryHQ/uv/releases/download"
    DEFAULT_UV_VERSION = "0.6.14"
    # Mapping of platform+arch to binary package name
    UV_PACKAGES = {
        "darwin-arm64": "uv-aarch64-apple-darwin.tar.gz",
        "darwin-x64": "uv-x86_64-apple-darwin.tar.gz",
        "windows-arm64": "uv-aarch64-pc-windows-msvc.zip",
        "windows-ia32": "uv-i686-pc-windows-msvc.zip",
        "windows-x64": "uv-x86_64-pc-windows-msvc.zip",
        "linux-arm64": "uv-aarch64-unknown-linux-gnu.tar.gz",
        "linux-ia32": "uv-i686-unknown-linux-gnu.tar.gz",
        "linux-ppc64": "uv-powerpc64-unknown-linux-gnu.tar.gz",
        "linux-ppc64le": "uv-powerpc64le-unknown-linux-gnu.tar.gz",
        "linux-s390x": "uv-s390x-unknown-linux-gnu.tar.gz",
        "linux-x64": "uv-x86_64-unknown-linux-gnu.tar.gz",
        "linux-armv7l": "uv-armv7-unknown-linux-gnueabihf.tar.gz",
        # MUSL variants
        "linux-musl-arm64": "uv-aarch64-unknown-linux-musl.tar.gz",
        "linux-musl-ia32": "uv-i686-unknown-linux-musl.tar.gz",
        "linux-musl-x64": "uv-x86_64-unknown-linux-musl.tar.gz",
        "linux-musl-armv6l": "uv-arm-unknown-linux-musleabihf.tar.gz",
        "linux-musl-armv7l": "uv-armv7-unknown-linux-musleabihf.tar.gz",
    }

    def __init__(self, version: str = DEFAULT_UV_VERSION, install_dir: Optional[str] = None):
        """
        Initialize the UvInstaller.
        
        Args:
            version: Version of uv to install (default: DEFAULT_UV_VERSION)
            install_dir: Directory to install uv (default: ~/.cherrystudio/bin)
        """
        self.version = version
        self.install_dir = install_dir or os.path.join(os.path.expanduser("~"), ".cherrystudio", "bin")

        self.arch = self.detect_arch()
        self.is_musl = self.detect_is_musl()

    @staticmethod
    def detect_arch():
        """Detects current platform and architecture."""
        arch = os.uname().machine if hasattr(os, "uname") else os.environ.get("PROCESSOR_ARCHITECTURE", "")
        
        # Normalize some architecture names
        if arch == "x86_64":
            arch = "x64"
        elif arch == "amd64":
            arch = "x64"
        elif arch == "i386":
            arch = "ia32"
        elif arch == "aarch64":
            arch = "arm64"
        
        return arch
    
    @staticmethod
    def detect_is_musl() -> bool:
        """Attempts to detect if running on MUSL libc."""

        if platform.system().lower() != 'linux':
            return False
        
        try:
            # Simple check for Alpine Linux which uses MUSL
            if os.path.exists("/etc/os-release"):
                with open("/etc/os-release", "r") as f:
                    content = f.read().lower()
                    return "alpine" in content
        except Exception:
            pass
        
        # Alternative check using ldd
        try:
            result = subprocess.run(["ldd", "--version"], capture_output=True, text=True)
            return "musl" in result.stdout.lower()
        except Exception:
            pass
        
        return False

    def download_file(self, url: str, dest_path: str) -> None:
        """Download a file from URL to destination path with progress."""

        def _download_with_curl(url: str, dest_path: str) -> None:
            """使用 curl 下载（macOS/Linux 默认安装）"""
            cmd = [
                "curl", "-L", "--progress-bar",
                "--output", dest_path,
                "--fail",  # 确保HTTP错误时退出非0
                url
            ]
            # subprocess.run(cmd, check=True)
            execude_command(cmd)

        def _download_with_wget(url: str, dest_path: str) -> None:
            """使用 wget 下载（Linux 常见，Windows需手动安装）"""
            cmd = [
                "wget", "--show-progress", "--progress=bar:force",
                "-O", dest_path,
                "--no-check-certificate",  # 跳过SSL验证（兼容性）
                url
            ]
            # subprocess.run(cmd, check=True)
            execude_command(cmd)

        def _download_with_builtin(url: str, dest_path: str) -> None:
            """最终回退方案（Python内置库）"""

            def report_hook(count: int, block_size: int, total_size: int) -> None:
                percent = int(count * block_size * 100 / total_size)
                mprint(f"\rDownloading... {percent}%", end="", flush=True)

            try:
                import urllib.request

                urllib.request.urlretrieve(url, dest_path, reporthook=report_hook)

            except Exception as e:
                raise RuntimeError(f"Failed to download uv packages: {str(e)}")
            
        mprint(f"Downloading from {url} to {dest_path}")
        # 尝试使用系统工具（按优先级顺序）
        tools = ["curl", "wget"]
        for tool in tools:
            try:
                if tool == "curl":
                    _download_with_curl(url, dest_path)
                elif tool == "wget":
                    _download_with_wget(url, dest_path)
                return
            except (subprocess.SubprocessError, FileNotFoundError):
                continue
       
        mprint("\nDownload completed")

        _download_with_builtin(url, dest_path)


    def install(self) -> bool:
        """
        Downloads and extracts the uv binary for the detected platform and architecture.
        
        Returns:
            bool: True if installation succeeded, False otherwise
        """
        if self.is_musl:
            platform_key = f"{platform.system().lower()}-musl-{self.arch}" 
        else:
            platform_key = f"{platform.system().lower()}-{self.arch}"

        package_name = self.UV_PACKAGES.get(platform_key)
        mprint(f"Installing uv {self.version} for {platform_key}")
        
        if not package_name:
            mprint(f"No binary available for {platform_key}", file=sys.stderr)
            return False
        
        # Create output directory structure
        os.makedirs(self.install_dir, exist_ok=True)

        # Download URL for the specific binary
        download_url = f"{self.UV_RELEASE_BASE_URL}/{self.version}/{package_name}"
        temp_dir = tempfile.gettempdir()
        temp_filename = os.path.join(temp_dir, package_name)

        try:
            mprint(f"Downloading uv {self.version} for {platform_key}...")
            mprint(f"URL: {download_url}")
            self.download_file(download_url, temp_filename)
            mprint(f"Extracting {package_name} to {self.install_dir}...")

            #############################
            # Windows zip file:
            #   uv.zip
            #   ├── uv    (可执行文件)
            #   └── uvx   (可执行文件)
            #
            # Unix-link tar.gz file:
            #   uv.tar.gz
            #    uv-<platform>/
            #    ├── uv    (可执行文件)
            #    └── uvx   (可执行文件)
            #############################
            if package_name.endswith(".zip"):
                # Handle zip files
                with zipfile.ZipFile(temp_filename, "r") as zip_ref:
                    zip_ref.extractall(self.install_dir)

                os.unlink(temp_filename)
                print(f"Successfully installed uv {self.version} for {platform_key}")
                return True
            else:
                # Handle tar.gz files
                with tarfile.open(temp_filename, "r:gz") as tar_ref:
                    found_files = {m.name for m in tar_ref.getmembers() if m.isfile()}
                    
                    # Extract directly to install directory
                    for member in tar_ref:
                        if member.name in found_files:
                            # Remove the platform directory prefix
                            # uv-<platform>/
                            member.name = os.path.basename(member.name)
                            tar_ref.extract(member, self.install_dir)
                            
                            # Ensure executable permissions (non-Windows)
                            if platform.system() != "Windows":
                                dest_path = os.path.join(self.install_dir, member.name)
                                try:
                                    os.chmod(dest_path, 0o755)  # rwxr-xr-x
                                except OSError as e:
                                    print(f"Warning: Failed to set permissions for {member.name}: {e}", 
                                        file=sys.stderr)
                
                os.unlink(temp_filename)
                print(f"Successfully installed uv")
                return True
        
        except Exception as e:
            print(f"Error installing uv for {platform_key}: {e}", file=sys.stderr)

            if os.path.exists(temp_filename):
                try:
                    os.unlink(temp_filename)
                except OSError:
                    pass
            # Check if install_dir is empty and remove it if so
            try:
                if os.path.exists(self.install_dir) and not os.listdir(self.install_dir):
                    shutil.rmtree(self.install_dir)
                    print(f"Removed empty directory: {self.install_dir}")
            except OSError as cleanup_error:
                print(f"Warning: Failed to clean up directory: {cleanup_error}", file=sys.stderr)
            return False
    
    

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

        ams.ui.add_metashape_menu()

    else:
        installer.main()
        installer.print_paths()