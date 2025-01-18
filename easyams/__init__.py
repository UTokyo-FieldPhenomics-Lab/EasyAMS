__version__ = "v0.0.1"

import sys
import os
import platform as pf
import Metashape

from .installer import whl_down, Installer

## get the script path
package_root, _ = os.path.split(os.path.realpath(__file__))  # E:\Github\EasyAMS\easyams\__init__.py -> head\file_name

machine = pf.machine()

# get current platform
if sys.platform.startswith("win"):
    platform = "win"
elif sys.platform.startswith("darwin"):
    platform = "mac"
else:
    platform = "linux"


# get python version in Metashape
py_version = f"{sys.version_info.major}.{sys.version_info.minor}"

## get the numpy download path
external_path = f'external.{platform}.{machine}.py{py_version}'
external_dir = os.path.join(package_root, external_path)
numpy_dir = os.path.join(external_dir, 'numpy')

# create external folder if not exists
if not os.path.exists(external_dir):
    os.mkdir(external_dir)

# can not find numpy folder -> first time run, need to download & zip numpy.whl
if not os.path.exists(numpy_dir):

    # if download link available, download and using progress bar to show progress
    if machine not in whl_down[platform].keys() or py_version not in whl_down[platform][machine].keys():
        Metashape.app.messageBox(
            f"[EasyAMS plugin]\nCould not find download link for numpy on {platform}-{machine}"
            f" and python {py_version}, please contact the author via EasyAMS github.")
    else:
        numpy_url = whl_down[platform][machine][py_version]
        # print(platform, machine, py_version, numpy_url)
        downloader = Installer(package_root, numpy_url, external_path)

sys.path.append(external_dir)

# check if successfully installed
try:
    import numpy as np
    print(np.array([1,2,3]))
    package_ready = True
except ImportError as e:
    print("Fail to load numpy")
    package_ready = False
