# EasyAMS

Easy Agisoft MetaShape (EasyAMS) Plugin with extended functions for smart agriculture.

![img](docs/_static/gui.jpg)

# How to use

> Please ensure you have the `Metashape Professional License` to have access to [automation option/Built-in python scripting](https://www.agisoft.com/features/compare/) function

Download the `tools/installer.py` in this project to your computer, and launch the `installer.py` script in the metashape to open the GUI.

![img](docs/_static/launch.png)

# Developer

## 1) Source code install

Please clone this repo to your local path.

Then Install this plugin by chosing the installer located at `/Your/Local/Path/to/EasyAMS/tools/installer.py` with argument `--dev`. 

![img](docs/_static/dev_setting.jpg)

It will use folder at `/Your/Local/Path/to/EasyAMS/src/easyams/` as `easyams` source code package, after any modification, restart Metashape to make effects.

If you have any modification for `installer.py`, rerun the `Run Python Script` with `--dev` arguement to refresh the cached installer file at `User\AppData\Local\Agisoft\Metashape Pro\scripts\easyams_launcher.py`. Please refer 
[How to run Python script automatically on Metashape Professional start : Helpdesk Portal](https://agisoft.freshdesk.com/support/solutions/articles/31000133123-how-to-run-python-script-automatically-on-metashape-professional-start) for more details.

## 2) Environment setup

Recommend using [uv](https://docs.astral.sh/uv/getting-started/installation/) as virtual enviroment manager.

```
> uv --version
uv 0.6.14
```

For example, the git repo folder is located at: `C:\path\to\source\code\EasyAMS` with the following folder structure:

```
C:\path\to\source\code\EasyAMS
├─ docs/
├─ src/
├─ tests/
readme.md
pyproject.toml
...
```

Using the following command to setup development enviroment:

```
> cd C:\path\to\source\code\EasyAMS
...EasyAMS > uv sync --all-groups
```

It will create a `.venv` at current project folder and install the `tests` dependency group and `train` dependency group inside `pyproject.toml`.

> PS: The default easyams plugin dependency is free of `pytorch` and `ultralytics`, only using the `onnx(cpu)` to inferencing and ensure the ease of installation.    
> For model training and exporting, `labelme` is used for data annotation and the `pytorch` package is required.


# Error Fixs

## Plugin installation

### 1. Python venv creation failed on Arch-Linux with `libcrypt` errors


```
[EasyAMS] [CMD] /home/crest/.local/share/Agisoft/Metashape Pro/easyams-packages-py39/bin/uv venv /home/crest/.local/share/Agisoft/Metashape Pro/easyams-packages-py39/venv --python 3.9.13
[EasyAMS] [Error]:
[EasyAMS]     × Querying Python at
[EasyAMS]     │ `/home/crest/.local/share/uv/python/cpython-3.9.13-linux-x86_64-gnu/bin/python3.9`
[EasyAMS]     │ failed with exit status exit status: 127
[EasyAMS]   
[EasyAMS]     │ [stderr]
[EasyAMS]     │ /home/crest/.local/share/uv/python/cpython-3.9.13-linux-x86_64-gnu/bin/python3.9:
[EasyAMS]     │ error while loading shared libraries: libcrypt.so.1: cannot open shared
[EasyAMS]     │ object file: No such file or directory
[EasyAMS]   
[EasyAMS] [EasyAMS] virtual isolated python venv creation failed
```

[Solution](https://github.com/electron-userland/electron-builder-binaries/issues/47): `sudo pacman -S --needed libxcrypt libxcrypt-compat` 