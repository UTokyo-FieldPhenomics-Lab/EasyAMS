import tkinter as tk
import Metashape

from easyams import __version__, package_ready
from easyams.utils import show_chunk_info, in_dev_info

if package_ready:
    window = tk.Tk()
    window.title(f"EasyAMS {__version__}")

    greeting = tk.Label(text="Welcome to use EasyAMS plugin")


    button1 = tk.Button(
        text="Show chunk info",
        width=25,
        # height=5,
        command=show_chunk_info
    )

    button2 = tk.Button(
        text="Batch import images",
        width=25,
        command=in_dev_info
    )

    button3 = tk.Button(
        text="Define ground by points",
        width=25,
        command=in_dev_info
    )

    button4 = tk.Button(
        text="Copy Bounding box",
        width=25,
        command=in_dev_info
    )


    greeting.pack()
    button1.pack()
    button2.pack()
    button3.pack()
    button4.pack()

    window.mainloop()
else:
    Metashape.app.messageBox(f"[EasyAMS Plugin]\nThe numpy dependices is not correctly installed, launch failed.")