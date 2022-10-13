import os
import zipfile
from urllib import request
import tkinter as tk
import tkinter.ttk as ttk

from easyams import __version__

# find the correct version of numpy dependices to download
whl_down = {
    "win": {
        "3.9": "https://github.com/UTokyo-FieldPhenomics-Lab/EasyAMS/releases/download/v0.0.1/numpy-1.22.4+vanilla-cp39-cp39-win_amd64.whl",
        "3.8": "https://github.com/UTokyo-FieldPhenomics-Lab/EasyAMS/releases/download/v0.0.1/numpy-1.22.4+vanilla-cp38-cp38-win_amd64.whl",
        "3.7": "https://github.com/UTokyo-FieldPhenomics-Lab/EasyAMS/releases/download/v0.0.1/numpy-1.21.5+vanilla-cp37-cp37m-win_amd64.whl",
        "3.6": "https://github.com/UTokyo-FieldPhenomics-Lab/EasyAMS/releases/download/v0.0.1/numpy-1.19.5+vanilla-cp36-cp36m-win_amd64.whl",
        "3.5": "https://github.com/UTokyo-FieldPhenomics-Lab/EasyAMS/releases/download/v0.0.1/numpy-1.16.6+vanilla-cp35-cp35m-win_amd64.whl",
    },
    "mac": {

    },
    "linux": {

    }
}


class Installer:
    # see https://stackoverflow.com/questions/59330620/python-tkinter-pop-up-progress-bar
    def __init__(self, package_root, download_link):
        self.package_root = package_root
        self.download_link = download_link

        ## get the numpy download path
        self.whl_path = os.path.join(self.package_root, 'external/numpy.whl')
        self.external_dir = os.path.join(self.package_root, 'external')
        self.numpy_dir = os.path.join(self.external_dir, 'numpy')

        # tkinter gui
        self.root = tk.Tk()
        self.root.title(f"EasyAMS {__version__}")

        self.notice_label = tk.Label(self.root, text="Downloading dependencies")
        self.notice_label.pack()

        self.progress_bar = ttk.Progressbar(self.root, orient="horizontal",
                                            length=400, mode="determinate")
        self.progress_bar.pack()
        self.progress_bar["maximum"] = 110

        center_window(self.root, width=400, height=50)

        self.download()

        self.root.mainloop()


    def reporthook(self, count, block_size, total_size):
        # See https://blog.shichao.io/2012/10/04/progress_speed_indicator_for_urlretrieve_in_python.html
        percent = min(int(count*block_size*100/total_size), 100)
        self.progress_bar["value"] = percent
        self.root.update()

    def save(self, url, filename):
        request.urlretrieve(url, filename, self.reporthook)

    def download(self):
        self.progress_bar["value"] = 0
        self.root.deiconify()
        self.save(self.download_link, self.whl_path)

        # unzip
        self.notice_label.config(text = "Unzipping dependices")
        with zipfile.ZipFile(self.whl_path, "r") as whl:
            whl.extractall(self.external_dir)
        self.progress_bar["value"] = 110
        self.root.update()

        # remove whl file
        self.notice_label.config(text = "Cleaning cache")
        os.remove(self.whl_path)

        self.root.destroy()


def center_window(root, width=300, height=200):
    # get screen width and height
    ws = root.winfo_screenwidth() # width of the screen
    hs = root.winfo_screenheight() # height of the screen

    # calculate x and y coordinates for the Tk root window
    x = (ws/2) - (width/2)
    y = (hs/2) - (height/2)

    # set the dimensions of the screen 
    # and where it is placed
    root.geometry('%dx%d+%d+%d' % (width, height, x, y))