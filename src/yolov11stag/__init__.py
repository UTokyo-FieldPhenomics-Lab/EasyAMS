# Ultralytics 🚀 AGPL-3.0 License - https://ultralytics.com/license

__version__ = "8.3.141"

import os

# Set ENV variables (place before imports)
if not os.environ.get("OMP_NUM_THREADS"):
    os.environ["OMP_NUM_THREADS"] = "1"  # default for reduced CPU utilization during training

from yolov11stag.models import YOLO
from yolov11stag.utils import SETTINGS
from yolov11stag.utils.checks import check_yolo as checks
from yolov11stag.utils.downloads import download

settings = SETTINGS
__all__ = (
    "__version__",
    "YOLO",
    "checks",
    "download",
    "settings",
)
