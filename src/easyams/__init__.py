__version__ = "0.1.6"


from . import (
    sahi_onnx, img_loader, ui, utils, web_api, gcp, updator, 
)

from .utils import (
    mprint, SystemInfo
)

import Metashape

system_info = SystemInfo()

def add_metashape_menu():
    # img loader function
    Metashape.app.addMenuItem("EasyAMS/Batch Import/Import RGB Images", img_loader.create_batch_image_loader)

    # stag_gcp function
    Metashape.app.addMenuItem("EasyAMS/GCP Markers/Export Marker GPS", gcp.gps_exporter.create_gps_exporter)
    Metashape.app.addMenuItem("EasyAMS/GCP Markers/Stag Markers/Detect Markers", gcp.stag_gcp.detect_stag_markers)
    # Metashape.app.addMenuItem("EasyAMS/StagMarkers/Print Markers", installer.print_paths)

    # -----------------------
    Metashape.app.addMenuSeparator("EasyAMS")

    # about easyams
    Metashape.app.addMenuItem("EasyAMS/Check for Updates", updator.check_updates_ui)
    Metashape.app.addMenuItem("EasyAMS/About EasyAMS", ui.show_about_dialog)

    # check for updates
    ver, has_updates = updator.check_updates()
    if has_updates:
        Metashape.app.messageBox("EasyAMS update available, please check for updates in the menu.")
