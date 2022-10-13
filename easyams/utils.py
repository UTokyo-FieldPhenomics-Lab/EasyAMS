import Metashape
from tkinter import messagebox as msgbox
from easyams import __version__

def show_chunk_info():
    docs = Metashape.app.document
    chunk = docs.chunk
    print(f"[EasyAMS {__version__}] {chunk.label}")

def in_dev_info():
    msgbox.showerror(title="Opps", message="This function is still in developing")