__version__ = "0.1.7"


from . import (
    sahi_onnx,
    batch_tools,
    ui,
    utils,
    gcp,
    updator,
)

from .utils import mprint, SystemInfo

import Metashape

system_info = SystemInfo()


def add_metashape_menu():
    # img loader function
    Metashape.app.addMenuItem(
        "EasyAMS/Batch Tools/Import RGB Images",
        batch_tools.images.create_batch_image_importer,
    )
    Metashape.app.addMenuItem(
        "EasyAMS/Batch Tools/Import Mask Images",
        batch_tools.masks.create_batch_mask_importer,
    )
    Metashape.app.addMenuItem(
        "EasyAMS/Batch Tools/Manage Markers",
        batch_tools.markers.create_batch_marker_manager,
    )
    Metashape.app.addMenuItem(
        "EasyAMS/Batch Tools/Remove Items",
        batch_tools.remove_items.create_batch_remove_items,
    )

    # stag_gcp function
    Metashape.app.addMenuItem(
        "EasyAMS/GCP Markers/Export Marker GPS", gcp.gps_exporter.create_gps_exporter
    )
    Metashape.app.addMenuItem(
        "EasyAMS/GCP Markers/Stag Markers/Detect Markers",
        gcp.stag_gcp.detect_stag_markers,
    )
    # Metashape.app.addMenuItem("EasyAMS/StagMarkers/Print Markers", installer.print_paths)

    # -----------------------
    Metashape.app.addMenuSeparator("EasyAMS")

    # about easyams
    Metashape.app.addMenuItem("EasyAMS/Check for Updates", updator.check_updates_ui)
    Metashape.app.addMenuItem("EasyAMS/About EasyAMS", ui.show_about_dialog)

    # check for updates
    updator.check_updates_on_startup()
