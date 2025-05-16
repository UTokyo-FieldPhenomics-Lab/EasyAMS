import cv2
import os
from PySide2 import QtWidgets, QtCore, QtGui

import numpy as np
import stag
import Metashape

from dataclasses import dataclass, field

from .sahi_onnx import AutoDetectionModel
from .sahi_onnx.predict import get_sliced_prediction

from .ui import ProgressDialog

def detect_stag_markers():
    app = QtWidgets.QApplication.instance()  # 获取当前Qt应用实例
    window = StagDetector(app.activeWindow())
    window.exec_()  # 使用exec_()而非show()确保模态性

class StagDetector(QtWidgets.QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Detect Markers")
        self.setMinimumSize(400, 250)

        from . import system_info
        self.system_info = system_info

        self.onnx = None
        self.init_onnx_file()

        self.create_ui()


    def init_onnx_file(self):
        # 检查是否需要更新
        is_outdated, local_version, github_version = self.system_info.onnx.outdated(return_versions=True)
        
        if is_outdated:
            print(f"[EasyAMS] Local YOLO.onnx file version v{local_version} is outdated, the latested Github release version v{github_version} is available.")
            self.system_info.onnx.update()
        else:
            print(f"[EasyAMS] Local YOLO.onnx file version v{local_version} is up-to-date.")


    def create_ui(self):

        layout = QtWidgets.QVBoxLayout()
        
        # Parameters Group
        params_group = QtWidgets.QGroupBox("Parameters")
        params_layout = QtWidgets.QFormLayout()

        # 1. Target Type
        self.target_type_combo = QtWidgets.QComboBox()
        self.target_type_combo.addItems(["Stag 11 bit", "Stag 13 bit", "Stag 15 bit", "Stag 17 bit", "Stag 19 bit", "Stag 21 bit", "Stag 23 bit"])
        self.target_type_combo.setCurrentIndex(4)  # Default to 'Stag 19 bit'
        params_layout.addRow("Target Type:", self.target_type_combo)

        # 2. Tolerance
        self.tolerance_input = QtWidgets.QSpinBox()
        self.tolerance_input.setRange(0, 100)
        self.tolerance_input.setValue(70)  # Default to 70
        self.tolerance_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.tolerance_slider.setRange(0, 100)
        self.tolerance_slider.setValue(70)
        self.tolerance_slider.valueChanged.connect(self.tolerance_input.setValue)
        self.tolerance_input.valueChanged.connect(self.tolerance_slider.setValue)
        
        tolerance_layout = QtWidgets.QHBoxLayout()
        tolerance_layout.addWidget(self.tolerance_input)
        tolerance_layout.addWidget(self.tolerance_slider)
        params_layout.addRow("Tolerance:", tolerance_layout)

        # 3. Max Residual
        self.max_residual_input = QtWidgets.QSpinBox()
        self.max_residual_input.setRange(0, 10000)
        self.max_residual_input.setValue(500)  # Default to 500
        self.max_residual_input.setSingleStep(100)  # 将步长设置为 100
        params_layout.addRow("Maximum Residual (pix):", self.max_residual_input)

        # 4. Process selected images only
        self.process_selected_checkbox = QtWidgets.QCheckBox("Process selected images only (in dev)")
        self.process_selected_checkbox.setEnabled(False)
        params_layout.addRow(self.process_selected_checkbox)

        # 5. Ignore masked image regions
        self.ignore_mask_checkbox = QtWidgets.QCheckBox("Ignore masked image regions (in dev)")
        self.ignore_mask_checkbox.setEnabled(False)
        params_layout.addRow(self.ignore_mask_checkbox)

        # 6. Merge with existing markers
        self.merge_with_exists_checkbox = QtWidgets.QCheckBox("Merge with existing markers (in dev)")
        self.merge_with_exists_checkbox.setEnabled(False)
        params_layout.addRow(self.merge_with_exists_checkbox)

        # 7. Execute on all chunks
        self.run_all_chunks = QtWidgets.QCheckBox("Run all chunks")
        self.run_all_chunks.setChecked(False)
        params_layout.addRow(self.run_all_chunks)

        # Close Parameters Group
        params_group.setLayout(params_layout)
        layout.addWidget(params_group)

        # OK and Cancel buttons
        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def get_parameters(self):
        return  {
            "code_bit": int(self.target_type_combo.currentText().split()[1]),
            "code_type": 'stag',
            "threshold": self.tolerance_input.value() / 100.0,
            "max_residual": self.max_residual_input.value(),
            "only_selected_img": self.process_selected_checkbox.isChecked(),
            "ignore_mask": self.ignore_mask_checkbox.isChecked(),
            "merge_with_exists": self.merge_with_exists_checkbox.isChecked(),
            "run_all_chunks": self.run_all_chunks.isChecked(),
        }

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
        # ignore the image rotations
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

    