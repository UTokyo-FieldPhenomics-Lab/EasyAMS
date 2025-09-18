import sys
import csv
from PySide2 import QtWidgets, QtCore, QtGui
from PySide2.QtWidgets import (QApplication, QDialog, QWidget, QVBoxLayout, 
                               QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem,
                               QFileDialog, QLineEdit, QLabel, QHeaderView)
from PySide2.QtCore import Qt

import Metashape

from easyams.utils import mprint

class GPS2CSVExporter(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setModal(True)  # 设置为模态对话框

        # UI design
        self.setWindowTitle("CSV Export Tool")
        self.setMinimumSize(600, 800)
        
        # Main layout
        self.layout = QVBoxLayout()
        
        # File path selection area
        self.file_layout = QHBoxLayout()
        self.file_layout.addWidget(QLabel("Output Path:"))
        
        self.path_edit = QLineEdit()
        self.file_layout.addWidget(self.path_edit)
        
        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.clicked.connect(self.browse_output_path)
        self.file_layout.addWidget(self.browse_btn)
        
        self.layout.addLayout(self.file_layout)
        
        # Filename input
        self.filename_layout = QHBoxLayout()
        self.filename_layout.addWidget(QLabel("Filename:"))
        
        self.filename_edit = QLineEdit("markers_gps.csv")
        self.filename_layout.addWidget(self.filename_edit)
        
        self.layout.addLayout(self.filename_layout)
        
        # Table display area
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Marker Label", "Lontitude", "Latitude", "Altitude"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        # Populate table with data
        self.populate_table()
        self.layout.addWidget(self.table)
        
        # Button area
        self.button_layout = QHBoxLayout()
        
        self.export_btn = QPushButton("Export CSV")
        self.export_btn.clicked.connect(self.export_csv)
        self.button_layout.addWidget(self.export_btn)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.close)
        self.button_layout.addWidget(self.cancel_btn)

        self.layout.addLayout(self.button_layout)
        
        self.setLayout(self.layout)
    

    def populate_table(self):
        # 获取当前活动的chunk
        chunk = Metashape.app.document.chunk

        """Fill table with markers data"""
        self.table.setRowCount(len(chunk.markers))

        self.csv_rows = []
        
        for row, marker in enumerate(chunk.markers):

            T = chunk.transform.matrix
            crs_position = chunk.crs.project(T.mulp(marker.position))
            x, y, z = crs_position
            x_str, y_str, z_str = f"{x:.12f}", f"{y:.12f}", f"{z:.12f}"

            target_item = QTableWidgetItem(marker.label)
            x_item = QTableWidgetItem(x_str)
            y_item = QTableWidgetItem(y_str)
            z_item = QTableWidgetItem(z_str)
            
            # 设置单元格不可编辑
            target_item.setFlags(target_item.flags() & ~Qt.ItemIsEditable)
            x_item.setFlags(x_item.flags() & ~Qt.ItemIsEditable)
            y_item.setFlags(y_item.flags() & ~Qt.ItemIsEditable)
            z_item.setFlags(z_item.flags() & ~Qt.ItemIsEditable)
            
            self.table.setItem(row, 0, target_item)
            self.table.setItem(row, 1, x_item)
            self.table.setItem(row, 2, y_item)
            self.table.setItem(row, 3, z_item)

            self.csv_rows.append( [marker.label, x_str, y_str, z_str] )
    
    def browse_output_path(self):
        """Select output directory"""
        directory = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if directory:
            self.path_edit.setText(directory)
    
    def export_csv(self):
        """Export data to CSV file"""
        directory = self.path_edit.text()
        filename = self.filename_edit.text()
        
        if not directory or not filename:
            QtWidgets.QMessageBox.warning(self, "Warning", "Please select output path and filename")
            return
        
        full_path = f"{directory}/{filename}"
        
        try:
            with open(full_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                for row in self.csv_rows:
                    writer.writerow(row)
            
            QtWidgets.QMessageBox.information(self, "Success", 
                                            f"CSV file successfully exported to:\n{full_path}")
            
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Export failed: {str(e)}")


def create_gps_exporter():
    app = QApplication.instance()  # 获取当前Qt应用实例
    window = GPS2CSVExporter(app.activeWindow())
    window.exec_()  # 使用exec_()而非show()确保模态性