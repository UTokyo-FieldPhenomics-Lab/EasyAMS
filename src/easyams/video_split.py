import os
import cv2
from PySide2 import QtWidgets, QtCore, QtGui
import Metashape


class VideoFrameExtractor(QtWidgets.QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("视频帧提取工具")
        self.setMinimumSize(800, 600)
        
        # 视频相关变量
        self.video_path = ""
        self.cap = None
        self.total_frames = 0
        self.fps = 0
        
        # 创建UI
        self.create_ui()
        
    def create_ui(self):
        layout = QtWidgets.QVBoxLayout()
        
        # 1. 视频文件选择
        video_group = QtWidgets.QGroupBox("视频文件")
        video_layout = QtWidgets.QHBoxLayout()
        self.video_path_label = QtWidgets.QLabel("未选择视频文件")
        video_btn = QtWidgets.QPushButton("选择视频")
        video_btn.clicked.connect(self.select_video)
        video_layout.addWidget(self.video_path_label, 1)
        video_layout.addWidget(video_btn)
        video_group.setLayout(video_layout)
        
        # 2. 输出目录选择
        output_group = QtWidgets.QGroupBox("输出目录")
        output_layout = QtWidgets.QHBoxLayout()
        self.output_path_label = QtWidgets.QLabel("未选择输出目录")
        output_btn = QtWidgets.QPushButton("选择目录")
        output_btn.clicked.connect(self.select_output_dir)
        output_layout.addWidget(self.output_path_label, 1)
        output_layout.addWidget(output_btn)
        output_group.setLayout(output_layout)
        
        # 3. 帧范围滑块
        frame_group = QtWidgets.QGroupBox("帧范围选择")
        frame_layout = QtWidgets.QVBoxLayout()
        
        # 预览窗口
        self.preview_label = QtWidgets.QLabel()
        self.preview_label.setAlignment(QtCore.Qt.AlignCenter)
        self.preview_label.setMinimumSize(640, 360)
        self.preview_label.setStyleSheet("background-color: black;")
        frame_layout.addWidget(self.preview_label)
        
        # 滑块控件
        self.range_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.range_slider.setRange(0, 100)
        self.range_slider.setValue(0)
        self.range_slider.sliderMoved.connect(self.update_frame_range)
        
        # 滑块数值显示
        slider_layout = QtWidgets.QHBoxLayout()
        self.start_frame_spin = QtWidgets.QSpinBox()
        self.start_frame_spin.setMinimum(0)
        self.start_frame_spin.valueChanged.connect(self.update_from_spin)
        
        self.end_frame_spin = QtWidgets.QSpinBox()
        self.end_frame_spin.setMinimum(1)
        self.end_frame_spin.valueChanged.connect(self.update_from_spin)
        
        slider_layout.addWidget(self.start_frame_spin)
        slider_layout.addWidget(self.range_slider)
        slider_layout.addWidget(self.end_frame_spin)
        frame_layout.addLayout(slider_layout)
        frame_group.setLayout(frame_layout)
        
        # 4. 帧间隔设置
        interval_group = QtWidgets.QGroupBox("帧间隔设置")
        interval_layout = QtWidgets.QHBoxLayout()
        interval_layout.addWidget(QtWidgets.QLabel("每隔多少帧提取一张:"))
        self.interval_spin = QtWidgets.QSpinBox()
        self.interval_spin.setMinimum(1)
        self.interval_spin.setMaximum(1000)
        self.interval_spin.setValue(30)
        interval_layout.addWidget(self.interval_spin)
        interval_group.setLayout(interval_layout)
        
        # 5. 执行按钮
        self.execute_btn = QtWidgets.QPushButton("提取帧并导入MetaShape")
        self.execute_btn.clicked.connect(self.execute_extraction)
        self.execute_btn.setEnabled(False)
        
        # 组装主布局
        layout.addWidget(video_group)
        layout.addWidget(output_group)
        layout.addWidget(frame_group)
        layout.addWidget(interval_group)
        layout.addWidget(self.execute_btn)
        
        self.setLayout(layout)
    
    def select_video(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "选择视频文件", "", "视频文件 (*.mp4 *.avi *.mov *.mkv)")
        if path:
            self.video_path = path
            self.video_path_label.setText(os.path.basename(path))
            self.load_video_info()
            self.execute_btn.setEnabled(True)
    
    def select_output_dir(self):
        path = QtWidgets.QFileDialog.getExistingDirectory(self, "选择输出目录")
        if path:
            self.output_path_label.setText(path)
    
    def load_video_info(self):
        """加载视频信息并初始化UI控件"""
        self.cap = cv2.VideoCapture(self.video_path)
        if not self.cap.isOpened():
            QtWidgets.QMessageBox.critical(self, "错误", "无法打开视频文件")
            return
        
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        
        # 初始化滑块和spinbox
        self.range_slider.setRange(0, self.total_frames - 1)
        self.start_frame_spin.setRange(0, self.total_frames - 1)
        self.end_frame_spin.setRange(1, self.total_frames)
        self.end_frame_spin.setValue(self.total_frames)
        
        # 显示第一帧
        self.update_preview(0)
    
    def update_frame_range(self, value):
        """滑块移动时更新帧范围"""
        self.start_frame_spin.setValue(value)
        self.update_preview(value)
    
    def update_from_spin(self):
        """spinbox值变化时更新滑块和预览"""
        start = self.start_frame_spin.value()
        end = self.end_frame_spin.value()
        
        if start >= end:
            self.start_frame_spin.setValue(end - 1)
            return
        
        self.range_slider.setValue(start)
        self.update_preview(start)
    
    def update_preview(self, frame_num):
        """更新预览窗口显示指定帧"""
        if not self.cap:
            return
            
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
        ret, frame = self.cap.read()
        if ret:
            # 转换颜色空间并缩放预览图
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, _ = frame.shape
            scale = min(640/w, 360/h)
            frame = cv2.resize(frame, (int(w*scale), int(h*scale)))
            
            # 显示到QLabel
            qimg = QtGui.QImage(
                frame.data, frame.shape[1], frame.shape[0], 
                QtGui.QImage.Format_RGB888)
            pixmap = QtGui.QPixmap.fromImage(qimg)
            self.preview_label.setPixmap(pixmap)
    
    def execute_extraction(self):
        """执行帧提取并导入MetaShape"""
        if not self.video_path or not self.output_path_label.text():
            QtWidgets.QMessageBox.warning(self, "警告", "请先选择视频文件和输出目录")
            return
            
        output_dir = self.output_path_label.text()
        start_frame = self.start_frame_spin.value()
        end_frame = self.end_frame_spin.value()
        frame_interval = self.interval_spin.value()
        
        # 执行帧提取
        success = self.video_to_frames(
            self.video_path, output_dir, 
            frame_interval, start_frame, end_frame)
        
        if success:
            # 导入到MetaShape
            self.import_to_metashape(output_dir)
            QtWidgets.QMessageBox.information(
                self, "完成", f"成功提取并导入了 {success} 张图片到当前chunk")
    
    def video_to_frames(self, video_path, output_dir, frame_interval=30, start_frame=0, end_frame=None):
        """改进后的帧提取函数，返回成功提取的帧数"""
        os.makedirs(output_dir, exist_ok=True)
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            QtWidgets.QMessageBox.critical(self, "错误", "无法打开视频文件")
            return 0
        
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if end_frame is None or end_frame > total_frames:
            end_frame = total_frames
        
        frame_count = 0
        saved_count = 0
        
        # 进度对话框
        progress = QtWidgets.QProgressDialog(
            "正在提取视频帧...", "取消", 0, end_frame - start_frame, self)
        progress.setWindowModality(QtCore.Qt.WindowModal)
        
        while True:
            ret, frame = cap.read()
            if not ret or frame_count > end_frame:
                break
                
            if start_frame <= frame_count <= end_frame and frame_count % frame_interval == 0:
                output_path = os.path.join(output_dir, f"frame_{saved_count:04d}.jpg")
                cv2.imwrite(output_path, frame)
                saved_count += 1
                
                # 更新进度
                progress.setValue(frame_count - start_frame)
                if progress.wasCanceled():
                    break
                
            frame_count += 1
        
        cap.release()
        progress.close()
        return saved_count
    
    def import_to_metashape(self, image_dir):
        """将图片导入到当前chunk"""
        doc = Metashape.app.document
        if not doc.chunk:
            doc.addChunk()
        
        # 获取所有图片文件
        image_files = []
        for f in os.listdir(image_dir):
            if f.lower().endswith(('.jpg', '.jpeg', '.png', '.tif', '.tiff')):
                image_files.append(os.path.join(image_dir, f))
        
        if not image_files:
            return
            
        # 添加到当前chunk
        doc.chunk.addPhotos(image_files)
        Metashape.app.update()
    
    def closeEvent(self, event):
        """关闭时释放视频资源"""
        if self.cap:
            self.cap.release()
        event.accept()

# 插件入口函数
def start_video_extractor():
    app = QtWidgets.QApplication.instance()
    parent = app.activeWindow()
    dialog = VideoFrameExtractor(parent)
    dialog.exec_()