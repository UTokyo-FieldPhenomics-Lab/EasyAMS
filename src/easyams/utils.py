import os
import re
import sys
import json
import platform
import hashlib
import requests
import shutil
import subprocess
import Metashape

from typing import Dict, Optional, Tuple

def mprint(*values, **kwargs):
    print(*values, **kwargs)
    Metashape.app.update()

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

class SystemInfo:

    def __init__(self):
        
        self.system = platform.system()

        self.metashape_user_script_folder = self.get_metashape_scripts_path()

        # current metashape buildin Python execuatable path
        self.metashape_python_executable_path = sys.executable

        # sys.version >>> '3.9.13 (main, Sep  9 2022, 11:31:02) \n[GCC 8.4.0]'
        self.metashape_python_version = sys.version.split(' ')[0] 

        self.easyams_plugin_folder = os.path.abspath(
            os.path.join(
                self.metashape_user_script_folder, 
                f"../easyams-packages-py{sys.version_info.major}{sys.version_info.minor}"))
        
        self.easyams_venv_folder = os.path.join(self.easyams_plugin_folder, ".venv")
        self.easyams_bin_folder = os.path.join(self.easyams_plugin_folder, "bin")

        self.easyams_model_folder = os.path.join(self.easyams_plugin_folder, "models")
        os.makedirs(self.easyams_model_folder, exist_ok=True)

        if shutil.which("uv") is not None:
            # uv is detected on this PC
            self.easyams_uv = "uv"
        else:
            # here assume that uv is installed in the easyams_bin_folder by installer.
            self.easyams_uv = os.path.join(self.easyams_bin_folder, "uv.exe" if self.system == "Windows" else "uv")

        self.onnx = GitReleaseDownloader(
            repo="UTokyo-FieldPhenomics-Lab/EasyAMS",  # 替换为实际的 GitHub 仓库路径
            save_folder=self.easyams_model_folder,  # 替换为实际的保存路径
            file_name="yolo11_stag",  # 文件基础名称
            suffix="onnx",  # 文件后缀
            # token="your_github_token"  # 可选：GitHub 个人访问令牌
        )

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
    

class GitReleaseDownloader:

    MAX_RELEASE_CHECKS = 5  # 最多检查多少个历史release

    def __init__(self, repo: str, save_folder: str, file_name: str, suffix: str, token: str = None):
        """
        初始化 GitReleaseDownloader 实例
        :param repo: GitHub 仓库路径，格式为 "org/repo"
        :param save_folder: 本地保存文件的路径
        :param file_name: 文件的基础名称（不包含版本号和后缀）
        :param suffix: 文件后缀（如 "onnx"）
        :param token: 可选，GitHub 个人访问令牌，用于认证
        """
        self.repo = repo
        self.save_folder = save_folder
        self.file_name = file_name
        self.suffix = suffix
        self.token = token
        self.headers = {"Authorization": f"token {token}"} if token else {}

        # 确保保存路径存在
        if not os.path.exists(save_folder):
            os.makedirs(save_folder, exist_ok=True)

    def local_version(self) -> int:
        """
        获取本地文件的版本号
        :return: 本地文件的版本号（整数），如果不存在则返回 0
        """
        pattern = re.compile(rf"{self.file_name}_v(\d+)\.{self.suffix}")
        files = os.listdir(self.save_folder)
        for file in files:
            match = pattern.match(file)
            if match:
                return int(match.group(1))
        return 0

    @property
    def file_path(self) -> str:
        local_version = self.local_version()

        return os.path.join(self.save_folder, f"yolo11_stag_v{local_version}.onnx")


    def _find_matching_asset(self, assets: list, version: Optional[int] = None) -> Tuple[Optional[int], Optional[str], Optional[str]]:
        """
        在assets列表中查找匹配的文件
        :param assets: GitHub Release的assets列表
        :param version: 如果指定，则查找特定版本的文件
        :return: (版本号, 下载URL, SHA256文件URL)
        """
        pattern = re.compile(rf"{self.file_name}_v(\d+)\.{self.suffix}")
        download_url = None
        found_version = None
        sha256_url = None
        for asset in assets:
            match = pattern.match(asset["name"])
            if match:
                current_version = int(match.group(1))
                if version is None or current_version == version:
                    found_version = current_version
                    if "sha256" not in asset["name"]:
                        download_url = asset["browser_download_url"]
                # 查找 SHA256 校验文件
                if asset["name"] == f"{self.file_name}_v{current_version}.sha256":
                    sha256_url = asset["browser_download_url"]
        return found_version, download_url, sha256_url

    def git_release_version(self, max_checks: int = MAX_RELEASE_CHECKS) -> int:
        """
        获取 GitHub Releases 中最新文件的版本号
        :param max_checks: 最多检查多少个历史release
        :return: 最新文件的版本号（整数）
        :raises: 如果没有找到匹配的文件，则抛出异常
        """
        # 首先检查最新release
        url = f"https://api.github.com/repos/{self.repo}/releases/latest"
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            release_data = response.json()
            version, _, _ = self._find_matching_asset(release_data.get("assets", []))
            if version is not None:
                return version
        # 如果最新release没有，则检查历史release
        url = f"https://api.github.com/repos/{self.repo}/releases"
        response = requests.get(url, headers=self.headers)
        if response.status_code != 200:
            raise Exception(f"Failed to fetch releases: {response.status_code}, {response.text}")
        releases = response.json()
        for i, release in enumerate(releases[:max_checks]):
            version, _, _ = self._find_matching_asset(release.get("assets", []))
            if version is not None:
                return version
        raise Exception(f"No matching file found in the last {max_checks} releases for pattern: {self.file_name}_v?.{self.suffix}")

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
        # 首先尝试最新release
        url = f"https://api.github.com/repos/{self.repo}/releases/latest"
        response = requests.get(url, headers=self.headers)

        if response.status_code == 200:
            release_data = response.json()
            latest_version, download_url, sha256_url = self._find_matching_asset(release_data.get("assets", []))
            if latest_version is not None:
                return self._download_and_verify(latest_version, download_url, sha256_url)
        
        # 如果最新release没有，则检查历史release
        url = f"https://api.github.com/repos/{self.repo}/releases"

        response = requests.get(url, headers=self.headers)
        if response.status_code != 200:
            mprint(f"Failed to fetch releases: {response.status_code}, {response.text}")
            return False

        releases = response.json()

        for release in releases[:self.MAX_RELEASE_CHECKS]:
            version, download_url, sha256_url = self._find_matching_asset(release.get("assets", []))
            if version is not None:
                return self._download_and_verify(version, download_url, sha256_url)
        
        mprint(f"No matching file found in the last {self.MAX_RELEASE_CHECKS} releases for pattern: {self.file_name}_v?.{self.suffix}")
        return False

    def _download_and_verify(self, version: int, download_url: str, sha256_url: Optional[str]) -> int:
        """
        下载文件并验证其完整性
        :param version: 文件版本号
        :param download_url: 文件下载URL
        :param sha256_url: SHA256校验文件URL
        :return: 下载的版本号
        """
        # 下载文件
        local_file_path = os.path.join(self.save_folder, f"{self.file_name}_v{version}.{self.suffix}")
        print(f"Downloading {download_url} to {local_file_path} ...")
        with requests.get(download_url, headers=self.headers, stream=True) as r:
            if r.status_code != 200:
                mprint(f"Failed to download file: {r.status_code}, {r.text}")
                return False
            with open(local_file_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        
        # 下载并校验 SHA256
        if sha256_url:
            print("Verifying file integrity using SHA256...")
            sha256_hash = self._download_sha256(sha256_url)
            if not self._verify_file_sha256(local_file_path, sha256_hash):
                os.remove(local_file_path)  # 删除下载的无效文件
                mprint("SHA256 verification failed. The downloaded file is corrupted or tampered.")
                return False
        else:
            print("Warning: No SHA256 checksum file found, skipping verification")
        
        # 删除旧文件
        self._delete_old_files(version)
        print(f"[EasyAMS] Update complete. Version: v{version}")
        return True

    def _download_sha256(self, sha256_url: str) -> str:
        """
        下载 SHA256 校验文件
        :param sha256_url: SHA256文件的URL
        :return: SHA256 校验值
        """
        response = requests.get(sha256_url, headers=self.headers)
        if response.status_code != 200:
            raise Exception(f"Failed to download SHA256 file: {response.status_code}, {response.text}")
        return response.text.strip()

    def _delete_old_files(self, latest_version: int):
        """
        删除旧版本的文件
        :param latest_version: 最新版本号
        """
        pattern = re.compile(rf"{self.file_name}_v(\d+)\.{self.suffix}")
        files = os.listdir(self.save_folder)
        for file in files:
            match = pattern.match(file)
            if match:
                version = int(match.group(1))
                if version < latest_version:
                    old_file_path = os.path.join(self.save_folder, file)
                    os.remove(old_file_path)
                    print(f"Deleted old file: {old_file_path}")

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