import os
import sys
import json
import platform
import Metashape

def mprint(*values, **kwargs):
    print(*values, **kwargs)
    Metashape.app.update()


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
        

        self.easyams_venv_folder = os.path.join(self.easyams_plugin_folder, "venv")

        self.onnx_file = None
        for file in os.listdir(self.easyams_plugin_folder):
            if "yolo11_stag_v" in file:
                self.onnx_file = os.path.join(self.easyams_plugin_folder, file)


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
    
class PathManager:

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

        self.config_file = os.path.join(self.easyams_plugin_folder, "config.json")

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
    
    def save_last_batch_import_path(self, path):
        """保存最后选择的路径到配置文件"""
        config = {}
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                config = json.load(f)
        config['last_batch_import_folder'] = path
        with open(self.config_file, 'w') as f:
            json.dump(config, f)
    
    def load_last_batch_import_path(self):
        """从配置文件加载最后选择的路径"""
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                return config.get('last_batch_import_folder', '')
        return ''