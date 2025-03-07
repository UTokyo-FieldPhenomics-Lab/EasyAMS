import os
import sys
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