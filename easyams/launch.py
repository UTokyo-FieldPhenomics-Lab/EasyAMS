import tkinter as tk
from tkinter import messagebox as msgbox
import Metashape

__version__ = "Beta 0.0.1"

docs = Metashape.app.document

def show_chunk_info():
    chunk = docs.chunk
    print(f"[EasyAMS {__version__}] {chunk.label}")

def in_dev_info():
    msgbox.showerror(title="Opps", message="This function is still in developing")


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

greeting.pack()
button1.pack()
button2.pack()
button3.pack()

window.mainloop()