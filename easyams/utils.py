import os
import Metashape

import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from tkinter import messagebox as msgbox

from easyams import __version__
from .tktooltip import CreateToolTip

def show_chunk_info():
    docs = Metashape.app.document
    chunk = docs.chunk
    print(f"[EasyAMS {__version__}] {chunk.label}")

def in_dev_info():
    msgbox.showerror(title="Opps", message="This function is still in developing")


class ImgLoaderPanel(tk.Toplevel):

    def __init__(self, master=None):

        super().__init__(master=master)

        self.root_path = tk.StringVar()
        self.use_cam_group = tk.IntVar()
        self.use_cam_group_kind = tk.IntVar()
        self.use_cam_group_split = tk.StringVar()

        self.use_cam_group.trace('w', self._cam_group_btn_change)
        self.use_cam_group_kind.trace('w', self._cam_group_btn_change)

        self.title("Batch Image Loader")
        self.geometry("600x1000")

        ###################
        # start folder selector #
        folder_selector_frame = tk.LabelFrame(self, text="Select the image folder for batch loading", padx=10, pady=10)

        folder_string_entry = tk.Entry(folder_selector_frame, textvariable=self.root_path)
        select_folder_btn = tk.Button(folder_selector_frame, text="...", command=self.open_root_folder)

        folder_string_entry.pack(fill="both", expand="yes", side="left")
        select_folder_btn.pack(expand="false", side="right", padx=(5,0))

        folder_selector_frame.pack(fill="x", expand="false", side="top", padx=10, pady=10)
        # end folder selector #
        ###################
        
        import_btn = tk.Button(self, text="Import")
        import_btn.pack(side='bottom', pady=5)
    
        ######################
        # subfolder selector #
        subfolder_selector = tk.LabelFrame(self, text="Set the subfolder relationship", padx=10, pady=10)

        #------------------
        # start cam_group options
        cam_grp_cbtn = tk.Checkbutton(subfolder_selector, text="Use camera group",
                                      variable=self.use_cam_group, onvalue=1, offvalue=0)
        # cam_grp_cbtn.bind("<Button>", self._cam_group_btn_onclick)
        cam_grp_cbtn.pack(anchor="nw")

        #...............
        # start optional panel
        self.cam_grp_frame = tk.Frame(subfolder_selector)
        
        self.cam_grp_btn1 = tk.Radiobutton(self.cam_grp_frame, text="Use subfolders as camera group",
                                           variable=self.use_cam_group_kind, value=0)
        self.cam_grp_btn2 = tk.Radiobutton(self.cam_grp_frame, text="Use saparator to camera group",
                                           variable=self.use_cam_group_kind, value=1)
        self.cam_grp_sp = tk.Entry(self.cam_grp_frame, textvariable=self.use_cam_group_split)

        # by default are diabled because use camera group is not enabled
        self.cam_grp_btn1.configure(state="disabled")
        self.cam_grp_btn2.configure(state="disabled")
        self.cam_grp_sp.configure(state="disabled")

        self.cam_grp_btn1.pack(anchor="nw", padx=(15,0))
        self.cam_grp_btn2.pack(anchor="nw", padx=(15,0))
        self.cam_grp_sp.pack(anchor="nw", padx=(40,0))

        btn1_ttp = CreateToolTip(self.cam_grp_btn1, \
            "Folder tree like:\n\n+ plot1\n   - subfolder1\n   - subfolder2\n   ...\n"
            "+ plot2\n   - subfolder1\n   - subfolder2\n ...\n\n"
            "Will get the following in Metashape: \n\n"
            "plot1 (chunk_name)\n> subfolder1 (camera_group_name)\n> subfolder2\n> ...\n"
            "plot2 \n> subfolder1\n> subfolder2\n> ...\n")

        btn2_ttp = CreateToolTip(self.cam_grp_btn2, \
            "For image folders like: \n\n* plot1_aaa_rotate1\n* plot1_aaa_rotate2\n  ...\n"
            "* plot2_aaa_rotate1\n* plot2_aaa_rotate2\n  ...\n\n"
            "using _aaa_ as seperator in the following inputbox:\n\n"
            "plot1 (chunk_name)\n> rotate1 (camera_group_name)\n> rotate2\n> ...\n"
            "plot2 \n> rotate1 \n> rotate2\n> ...\n")

        self.cam_grp_frame.pack(anchor="nw", expand='false')
        # end optional panel
        # .............

        # end camera group options
        #-------------------------

        hbar = ttk.Separator(subfolder_selector, orient="horizontal")
        hbar.pack(fill='x', padx=10, pady=10, expand='false')

        prev_label = tk.Label(subfolder_selector, text="Metashape import preview")
        prev_label.pack(anchor="nw")

        #...............
        # start tree panel
        tree_frame = tk.Frame(subfolder_selector)
        tree = ttk.Treeview(tree_frame)
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)

        tree.heading('#0', text="Workspace", anchor='nw')

        # test_data
        tree.insert('', tk.END, text='plot1', iid=0, open=True)
        tree.insert('', tk.END, text='plot2', iid=1, open=False)

        tree.insert('', tk.END, text='rotate1', iid=2, open=True)
        tree.insert('', tk.END, text='rotate2', iid=3, open=False)

        tree.insert('', tk.END, text='IMG_3487.JPG', iid=4, open=True)
        tree.insert('', tk.END, text='...', iid=5, open=True)
        tree.insert('', tk.END, text='IMG_3698.JPG', iid=6, open=True)

        tree.move(2, 0, 0)
        tree.move(3, 0, 1)

        tree.move(4, 2, 0)
        tree.move(5, 2, 1)
        tree.move(6, 2, 2)
        # end test data

        tree.pack(side="left", fill='both', expand='yes')
        vsb.pack(side="right", fill='y')

        update_btn = tk.Button(subfolder_selector, text="Update")
        update_btn.pack(side='bottom')

        tree_frame.pack(side='top', fill='both', expand='yes', padx=5, pady=5)
        # end tree panel
        # ..............

        subfolder_selector.pack(fill="both", expand="true", side="top", padx=10, pady=5)
        # end subfolder selector #
        ######################

    def open_root_folder(self):
        root_path = filedialog.askdirectory(title="Select the image folder to import")
        if root_path == '':
            raise ValueError("User cancelled folder selection")

        # check all image files in the folder
        subfolders = os.listdir(root_path)
        if len(subfolders) == 0:
            msgbox.showerror(title="Opps", message=f"Selected folder [{root_path}] is an empty folder")

        self.root_path.set(root_path)

    def _cam_group_btn_change(self, var=None, blank=None, mode=None):
        # disable all if not using the camera group
        if self.use_cam_group.get() == 0:
            for child in self.cam_grp_frame.winfo_children():
                child.configure(state='disabled')
        # use camera group
        elif self.use_cam_group.get() == 1:
            # activate two ratioclick btn
            self.cam_grp_btn1.configure(state='normal')
            self.cam_grp_btn2.configure(state='normal')
            # using the subfolder as the camera group, disable entry
            if self.use_cam_group_kind.get() == 0:
                self.cam_grp_sp.configure(state='disabled')
            elif self.use_cam_group_kind.get() == 1:
                self.cam_grp_sp.configure(state='normal')
            else:
                raise ValueError(f"Invalid value for [self.use_cam_group_kind] = {self.use_cam_group_kind.get()}")
        else:
            raise ValueError(f"Invalid value for [self.use_cam_group] = {self.use_cam_group.get()}")


def img_loader(parent_tk_window):
    ilp = ImgLoaderPanel(parent_tk_window)
