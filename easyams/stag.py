import cv2
import os
from PySide2 import QtCore

import numpy as np
import Metashape

from .sahi_onnx import AutoDetectionModel
from .sahi_onnx.predict import get_sliced_prediction

from .utils import mprint
from .ui import ProgressDialog

def detect_stag_markers():
    doc = Metashape.app.document
    chunk = doc.chunk

    from . import system_info
    # 检查 onnx 文件是否存在
    if system_info is None or not os.path.exists(system_info.onnx_file):
        raise FileNotFoundError("[EasyAMS] could not find onnx file")
    
    # here need to popup a ui with following choices
    # :target type: stag HD17, stag HD19, etc
    # :Tolerance: 0-1, # confidence threshold of model
    # :maximum residual (pixel): 500 (by default, not execeed 1000 for stag-python detection)
    # :process selected images only: bool
    # :ignore masked image regions: bool
    params = {
        "target_type": "HD19",
        "onnx_model_path": system_info.onnx_file,
        "threshold": 0.7,
        "max_residual": 500,
        "only_selected_img": False,
        "ignore_mask": False
    }

    # 创建进度对话框
    progress_dialog = ProgressDialog()
    progress_dialog.show()

    # 创建并启动线程
    thread = DetectMarkersThread(chunk, params, progress_dialog)
    # thread.start()
    thread.run()

# class DetectMarkersThread(QtCore.QThread):
class DetectMarkersThread:
    def __init__(self, chunk, params, progress_dialog):
        super().__init__()
        self.chunk = chunk
        self.cameras = chunk.cameras
        self.params = params
        self.progress_dialog = progress_dialog

    def run(self):
        
        # 初始化 YOLO 检测器
        yolo = StagYoloDetector(self.params['onnx_model_path'], thresh=self.params['threshold'])

        self.progress_dialog.update_total_progress(10)  # 10%

        # 总进度
        total_cameras = len(self.cameras)
        for i, camera in enumerate(self.cameras):
            # 更新总进度
            total_progress = 10 + int((i + 1) / total_cameras * 80)
            self.progress_dialog.update_total_progress(total_progress)

            # 处理每个相机
            self.process_camera(camera, yolo)

        # back results to chunks

    def process_camera(self, camera, yolo):
        self.progress_dialog.update_sub_progress(0)

        # read cv2 to memory
        img_array = cv2.imread(camera.photo.path)
        self.progress_dialog.update_sub_progress(10)

        # 实际检测逻辑
        detections = yolo.get_detection(img_array)
        self.progress_dialog.update_sub_progress(70)

        for detection in detections:
            mprint(f"Bounding Box: {detection.bbox.to_xyxy()}, Confidence: {detection.score.value}")


class StagYoloDetector:

    def __init__(self, onnx_model_path:str, thresh:float=0.7):
        """Detect Stag by Yolov10
        """
        self.detection_model = AutoDetectionModel.from_pretrained(
            model_type='yolov8onnx',
            model_path=onnx_model_path,
            confidence_threshold=thresh,
            category_mapping={'0': "stag"},
            device="cpu"
        )

    def get_detection(self, img_array:np.ndarray, ):
        result = get_sliced_prediction(
            img_array,
            self.detection_model,
            slice_height=512,
            slice_width=512,
            overlap_height_ratio=0.2,
            overlap_width_ratio=0.2,
        )

        return result.object_prediction_list


class StagGenerator:

    def __init__(self):
        pass

    