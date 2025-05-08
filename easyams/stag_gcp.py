import cv2
import os
# from PySide2 import QtCore

import numpy as np
import Metashape

import stag

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
        "code_bit": 19,
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

def detect_all_stag_markers():
    doc = Metashape.app.document
    chunks = doc.chunks

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
        "code_bit": 19,
        "onnx_model_path": system_info.onnx_file,
        "threshold": 0.7,
        "max_residual": 500,
        "only_selected_img": False,
        "ignore_mask": False
    }


    for chunk in chunks:
        if not chunk.enabled:
            pass

        mprint(f"[EasyAMS] Processing chunk [{chunk.label}]")

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
            
            # self.process_camera_stag_native(camera, self.params['code_bit'])

        # back results to chunks

    def process_camera_stag_native_api(self, camera, code_bit):
        # read cv2 to memory
        img_array = cv2.imread(camera.photo.path, cv2.IMREAD_COLOR|cv2.IMREAD_IGNORE_ORIENTATION)

        (corners, ids, rejected_corners) = stag.detectMarkers(img_array, code_bit)

        if len(ids) == 1:  # only accept one marker detection results
            marker_corner = np.squeeze(corners[0], axis=0)

            # calculate center
            marker_center = np.sum(marker_corner, axis=0) / 4

            marker_id = ids[0][0]

            if marker_id is not None:
                # marker_center = marker_center_in_bbox + bbox_offset
                mprint(f"[EasyAMS] detected Stag HD{self.params['code_bit']}-{marker_id} at ({marker_center[0]}, {marker_center[1]})")

                marker_label = f"StagHD{self.params['code_bit']}-{marker_id}"

                self.place_marker_on_photo(self.chunk, camera, marker_label, marker_center)


    def process_camera(self, camera, yolo):
        self.progress_dialog.update_sub_progress(0)
        mprint(f"[EasyAMS] processing image [{camera.label}] ")

        # read cv2 to memory
        img_array = cv2.imread(camera.photo.path, cv2.IMREAD_COLOR|cv2.IMREAD_IGNORE_ORIENTATION)
        self.progress_dialog.update_sub_progress(10)
        mprint(f"    |--- image read with size [{img_array.shape}] ")

        # actual detection process
        detections = yolo.get_detection(img_array)
        self.progress_dialog.update_sub_progress(50)

        # remove too large detections
        filtered_detections = yolo.filter_results(detections, self.params['max_residual'])
        filtered_detection_num = len(filtered_detections)
        mprint(f"    |--- filtered out {filtered_detection_num} of total {len(detections)} detections mets maximum residual {self.params['max_residual']} pixels")
        for detection in filtered_detections:
            mprint(f"    |    |--- {detection.bbox.to_xyxy()}, Confidence: {detection.score.value}")
        self.progress_dialog.update_sub_progress(60)

        # using stag-python to detect markers
        for i, detection in enumerate(detections):
            cropped_imarray, x0, y0 = yolo.crop_image(img_array, detection.bbox.to_xyxy())

            bbox_offset = np.asarray([x0, y0])

            marker_id, \
            marker_center_in_bbox, \
            marker_corner_in_bbox = yolo.stag_detect_id_in_bbox(
                cropped_imarray, 
                self.params['code_bit']
            )

            if marker_id is not None:
                marker_center = marker_center_in_bbox + bbox_offset
                mprint(f"    |--- detected Stag HD{self.params['code_bit']}-{marker_id} at ({marker_center[0]}, {marker_center[1]})")

                marker_label = f"StagHD{self.params['code_bit']}-{marker_id}"

                self.place_marker_on_photo(self.chunk, camera, marker_label, marker_center)


    def place_marker_on_photo(self, chunk, camera, marker_label, marker_center):
        """
        Adds a marker to a Metashape photo with the given label and coordinates.
        If the marker with the same label already exists, updates its position.

        :param camera: Metashape.Camera object where the marker will be placed.
        :param marker_label: Label for the marker (string).
        :param marker_center: Marker coordinates in the photo (tuple of floats, e.g., (x, y)).
        """
        # Check if a marker with the same label already exists
        existing_marker = None
        for marker in chunk.markers:
            if marker.label == marker_label:
                existing_marker = marker
                break

        if existing_marker:
            # Update the existing marker's projection
            existing_marker.projections[camera] = Metashape.Marker.Projection(marker_center, True)
            print(f"    |--- Updated marker '{marker_label}' on camera '{camera.label}' at {marker_center}.")
        else:
            # Create a new marker
            marker = chunk.addMarker()
            marker.label = marker_label
            marker.projections[camera] = Metashape.Marker.Projection(marker_center, True)
            print(f"    |--- Added new marker '{marker_label}' on camera '{camera.label}' at {marker_center}.")


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
            slice_height=1024,
            slice_width=1024,
            overlap_height_ratio=0.2,
            overlap_width_ratio=0.2,
        )

        return result.object_prediction_list
    
    def filter_results(self, detections, bbox_size=500):
        """
        Filters out bounding boxes with width or height larger than the given bbox_size.
        
        Args:
            detections (list): List of detection results.
            bbox_size (int): Maximum allowed size for bounding box width or height.
        
        Returns:
            list: Filtered list of detection results.
        """
        filtered_results = []
        for detection in detections:
            x1, y1, x2, y2 = detection.bbox.to_xyxy()
            width = x2 - x1
            height = y2 - y1
            if width <= bbox_size and height <= bbox_size:
                filtered_results.append(detection)
        return filtered_results
    
    @staticmethod
    def crop_image(imarray:np.ndarray, bbox):
        x1, y1, x2, y2 = bbox
        xbuffer = np.ceil( abs(x1-x2) * 0.1).astype(int)
        ybuffer = np.ceil( abs(y1-y2) * 0.1).astype(int)

        # Compute new coordinates considering the buffer
        x_start = int(max(x1 - xbuffer, 0))
        x_end   = int(min(x2 + xbuffer, imarray.shape[1] - 1))
        y_start = int(max(y1 - ybuffer, 0))
        y_end   = int(min(y2 + ybuffer, imarray.shape[0] - 1))

        # Check if the cropped region is valid (non-zero area)
        if x_start < x_end and y_start < y_end:
            cropped_image = imarray[y_start:y_end, x_start:x_end]
            return cropped_image, x_start, y_start
        else:
            raise BufferError(f"Invalid bounding box with buffer [{x_start}:{x_end}, {y_start}:{y_end}]. Cropped region has zero area.")
        
    @staticmethod
    def stag_detect_id_in_bbox(imarray:np.ndarray, code_bit:int):
        # detect each bbox
        (corners, ids, rejected_corners) = stag.detectMarkers(imarray, code_bit)

        if len(ids) == 1:  # only accept one marker detection results
            marker_corner = np.squeeze(corners[0], axis=0)

            # calculate center
            marker_center = np.sum(marker_corner, axis=0) / 4

            return ids[0][0], marker_center, marker_corner
        else:
            return None, None, None

class StagGenerator:

    def __init__(self):
        pass

    