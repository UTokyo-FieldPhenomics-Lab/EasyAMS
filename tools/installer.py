__version__ = "0.0.4"

import os
import sys
import platform
import shutil
import subprocess
from packaging.version import Version

# uv installer dependencies
import tempfile
import tarfile
import zipfile

# config manager
import json

from typing import Dict, Optional, Tuple

import Metashape

def mprint(*values, **kwargs):
    prefixed_values = ["[EasyAMS]"] + list(values)
    print(*prefixed_values, **kwargs)
    Metashape.app.update()

def path_equal(path1, path2):
    abs_path1 = os.path.abspath(os.path.normpath(path1))
    abs_path2 = os.path.abspath(os.path.normpath(path2))
    return abs_path1 == abs_path2

def execude_command(cmd, workdir=None):
    mprint(f"[CMD] {' '.join(cmd)}")

    try:
        # 使用 Popen 执行命令
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', cwd=workdir)

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

def download_file(url: str, dest_path: str) -> None:
    """Download a file from URL to destination path with progress."""

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

class Installer:

    def __init__(self):

        self.check_campatibility()
        
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
        self.is_dev = False

        self.config_file = os.path.join(self.easyams_plugin_folder, "config.json")
        self.config_manager = ConfigManager(self.config_file)

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
        if Version(Metashape.app.version) < Version("2.1.0"):
            Metashape.app.messageBox("[EasyAMS] Your version of Metashape is may outdated. Please update to the version over 2.1.0 to ensure the best performance.")

    def is_blank_metashape_project(self):
        doc = Metashape.app.document
        if len(doc.chunks) != 1 or doc.chunk.label != "Chunk 1" or len(doc.chunk.cameras) != 0:
            Metashape.app.messageBox("[EasyAMS] This is not a blank Metashape project. Please save your current work and create a new blank project before running the script.")
            return False
        else:
            return True
    
    def print_paths(self):
        mprint(f"[EasyAMS] Platform: {self.system}")
        mprint(f"[EasyAMS] Metashape Buildin Python Executable Path: {self.metashape_python_executable_path}")
        mprint(f"[EasyAMS] User Plugin Script Path: {self.metashape_user_script_folder}")
        mprint(f"[EasyAMS] Current Installer Path: {self.easyams_installer_folder}")

    def in_dev_mode(self):
        self.is_dev = True
        self.config_manager.save("is_dev", self.is_dev)
        
    def is_uv_installed(self) -> bool:
        """
        Returns
        -------
        bool
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
        
    def install_easyams_dependencies(self):
        mprint(f'[EasyAMS][Func] Installing dependencies...')

        if self.venv_is_ready or self.venv_ready():

            if self.is_dev:
                cmd = [
                    self.easyams_uv,
                    "pip",
                    "install",
                    "-e",
                    # easyams/tools/ -> easyams/ as dev root path
                    os.path.dirname( self.easyams_installer_folder )
                ]

            else:
                cmd = [
                    self.easyams_uv,
                    "pip",
                    "install",
                    "-U",
                    "easyams"
                ]

            is_okay = execude_command(cmd, workdir=self.easyams_venv_folder)
            if is_okay:
                mprint("[EasyAMS] Dependencies installed successfully.")
                # Metashape.app.messageBox("EasyAMS dependencies successfully installed.")
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

                # link editable easyams folder for dev
                self._add_pip_linked_install(site_packages_folder)

            else:
                Metashape.app.messageBox(
                    f"[EasyAMS] venv missing site-package folders of '{site_packages_folder}'"
                )

    def _add_pip_linked_install(self, site_packages_folder):
        for item in os.listdir(site_packages_folder):
            if not ( item.endswith('.egg-link') or  item.endswith('.pth') ):
                continue

            if not 'easyams' in item:
                continue

            with open(os.path.join(site_packages_folder, item), 'r') as f:
                # .egg-link / .pth 文件的第一行是包的路径
                package_path = f.readline().strip()
                if os.path.exists(package_path):
                    mprint(f'inserting .egg-link or .pth {package_path} to path')
                    sys.path.insert(0, package_path)

    def copy_installer_to_launch_folder(self):
        """
        将当前运行的 Python 脚本复制到指定目录
        :param target_dir: 目标目录，如果为 None 则使用 self.save_path
        """
        # 获取当前运行的脚本路径
        current_script = os.path.abspath(__file__)
        target_path = os.path.join(self.metashape_user_script_folder, 'easyams_launcher.py')
        mprint(target_path)
        
        # 如果目标路径与当前路径相同，则跳过
        if os.path.abspath(target_path) == os.path.abspath(current_script):
            print(f"[Info] Source and destination are the same: {current_script}")
            return
            
        try:
            # 复制文件
            shutil.copy2(current_script, target_path)
            print(f"[Success] Copied installer to: {target_path}")
        except Exception as e:
            print(f"[Error] Failed to copy installer: {str(e)}")
            raise


    def main(self):
        if not self.is_blank_metashape_project():
            return

        mprint("[EasyAMS] Initializing the plugin...")

        if not self.is_uv_installed():
            raise FileNotFoundError("[EasyAMS] Can not find system uv or plugin bulit-in uv for setting up dependencies")

        # create virtual envs
        if not self.venv_ready():
            self.create_venv()

        if self.venv_is_ready or self.venv_ready():

            self.install_easyams_dependencies()

            self.add_venv_to_path()

            self.copy_installer_to_launch_folder()

            self.print_paths()

            Metashape.app.messageBox("EasyAMS plugin installed successfully, restart Metashape to take effects")
            Metashape.app.quit()


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
            download_file(download_url, temp_filename)
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

class ConfigManager:

    def __init__(self, config_file):

        self.config_file = config_file
    
    def save(self, key, value):
        """保存最后选择的路径到配置文件"""
        config = {}
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                config = json.load(f)
        config[key] = value
        with open(self.config_file, 'w') as f:
            json.dump(config, f)
    
    def load(self, key):
        """从配置文件加载最后选择的路径"""
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                return config.get(key, '')
        return ''
        

if __name__ == "__main__":
    installer = Installer()

    if len(sys.argv) > 1:
        dev_option = ['--dev', '-D', '-d']
        try:
            if sys.argv[1] in dev_option:
                is_dev = True
                installer.in_dev_mode()
                mprint(f"Set to develop mode")
            else:
                is_dev = False
        except ValueError:
            mprint(f"Input developer mode value [{sys.argv[1]}] should in {dev_option}")


    if path_equal(installer.easyams_installer_folder, installer.metashape_user_script_folder):
        # the installer is installed correctly (inside the metashape script launcher folder)
        installer.add_venv_to_path()
        
        import easyams as ams

        ams.ui.add_metashape_menu()

    else:
        installer.main()