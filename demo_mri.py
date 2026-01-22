import sys
import numpy as np
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QSlider, QLabel, QSpinBox, QDoubleSpinBox,
                             QPushButton, QFileDialog, QGroupBox, QSplitter, QMessageBox)
from PyQt5.QtCore import Qt, QPoint, pyqtSignal, QRect
from PyQt5.QtGui import QImage, QPixmap, QPainter, QColor, QPen, QPolygon
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from scipy.ndimage import rotate
import matplotlib

# --- IMPORTS FOR NIFTI ---
try:
    import nibabel as nib
    from nibabel.processing import resample_to_output
except ImportError:
    nib = None

matplotlib.use('Qt5Agg')


class Cube3DNavigator(QWidget):
    """Interactive 3D cube widget with CT slice textures"""
    rotation_changed = pyqtSignal(float, float)
    view_changed = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(300, 300)
        self.rotation_x = 20
        self.rotation_y = 30
        self.last_pos = None
        self.data = None
        self.face_images = {}
        self.current_dominant_face = None
        
    def set_data(self, data):
        """Set CT data and create face textures. Assumes data shape is (Z, Y, X)."""
        self.data = data
        self.face_images = {}
        
        if data is not None and len(data.shape) >= 3:
            z, y, x = data.shape[0], data.shape[1], data.shape[2]
            
            # --- FIXED MAPPING FOR TEXTURES ---
            # Axial (Top/Bottom): Slicing Z (dim 0)
            axial_slice = data[z//2, :, :]
            
            # Coronal (Front/Back): Slicing Y (dim 1)
            coronal_slice = data[:, y//2, :]
            
            # Sagittal (Left/Right): Slicing X (dim 2)
            sagittal_slice = data[:, :, x//2]
            
            # Convert to QImage for each face
            self.face_images['top'] = self.array_to_qimage(axial_slice)
            self.face_images['bottom'] = self.array_to_qimage(axial_slice)
            
            self.face_images['front'] = self.array_to_qimage(coronal_slice)
            self.face_images['back'] = self.array_to_qimage(coronal_slice)
            
            self.face_images['left'] = self.array_to_qimage(sagittal_slice)
            self.face_images['right'] = self.array_to_qimage(sagittal_slice)
            
        self.update()
    
    def array_to_qimage(self, array):
        """Convert numpy array to QImage with memory safety fixes"""
        arr_min, arr_max = array.min(), array.max()
        if arr_max > arr_min:
            normalized = ((array - arr_min) / (arr_max - arr_min) * 255).astype(np.uint8)
        else:
            normalized = np.zeros_like(array, dtype=np.uint8)
        
        height, width = normalized.shape
        bytes_per_line = width
        
        # --- MEMORY SAFETY FIX ---
        if not normalized.flags['C_CONTIGUOUS']:
            normalized = np.ascontiguousarray(normalized)
            
        # Create a copy of the bytes to ensure QImage owns the data
        # .tobytes() creates a copy, preventing the memoryview error
        data_bytes = normalized.tobytes()
        
        qimage = QImage(data_bytes, width, height, bytes_per_line, QImage.Format_Grayscale8)
        return qimage.copy()
    
    def mousePressEvent(self, event):
        self.last_pos = event.pos()
    
    def mouseMoveEvent(self, event):
        if self.last_pos is not None:
            dx = event.x() - self.last_pos.x()
            dy = event.y() - self.last_pos.y()
            
            self.rotation_y += dx * 0.5
            self.rotation_x += dy * 0.5
            
            self.rotation_x = max(-180, min(180, self.rotation_x))
            self.rotation_y = self.rotation_y % 360
            
            self.last_pos = event.pos()
            self.update()
            
            self.rotation_changed.emit(self.rotation_x, self.rotation_y)
            self.check_dominant_face()
    
    def mouseReleaseEvent(self, event):
        self.last_pos = None
    
    def check_dominant_face(self):
        """Determine which face is most visible and switch view"""
        import math
        rx = self.rotation_x
        ry = self.rotation_y % 360
        
        if ry > 180:
            ry = ry - 360
        
        # --- FIXED MAPPING FOR AUTO-SWITCHING ---
        if abs(rx) < 45 and abs(ry) < 45:
            dominant = 'coronal'
        elif abs(rx) < 45 and abs(ry - 180) < 45:
            dominant = 'coronal'
        elif abs(rx) < 45 and (abs(ry - 90) < 45 or abs(ry + 90) < 45):
            dominant = 'sagittal'
        elif (abs(rx - 90) < 45 or abs(rx + 90) < 45):
            dominant = 'axial'
        else:
            dominant = self.current_dominant_face
        
        if dominant and dominant != self.current_dominant_face:
            self.current_dominant_face = dominant
            self.view_changed.emit(dominant)
    
    def draw_textured_face(self, painter, points, face_key, color):
        if len(points) < 4: return
        
        min_x, max_x = min(p[0] for p in points), max(p[0] for p in points)
        min_y, max_y = min(p[1] for p in points), max(p[1] for p in points)
        width, height = int(max_x - min_x), int(max_y - min_y)
        
        if width <= 0 or height <= 0: return
        
        if face_key in self.face_images:
            qimage = self.face_images[face_key]
            scaled = qimage.scaled(width, height, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
            polygon = QPolygon([QPoint(int(p[0]), int(p[1])) for p in points])
            
            painter.setOpacity(0.8)
            painter.drawImage(int(min_x), int(min_y), scaled)
            painter.setOpacity(1.0)
            
            painter.setPen(QPen(QColor(200, 200, 200), 2))
            painter.setBrush(Qt.NoBrush)
            painter.drawPolygon(polygon)
        else:
            painter.setBrush(color)
            painter.setPen(QPen(QColor(200, 200, 200), 1))
            polygon = QPolygon([QPoint(int(p[0]), int(p[1])) for p in points])
            painter.drawPolygon(polygon)
        
        center_x = sum(p[0] for p in points) / len(points)
        center_y = sum(p[1] for p in points) / len(points)
        
        painter.setPen(QColor(255, 255, 0))
        label_map = {
            'front': 'CORONAL',
            'back': 'CORONAL',
            'left': 'SAGITTAL',
            'right': 'SAGITTAL',
            'top': 'AXIAL',
            'bottom': 'AXIAL'
        }
        painter.drawText(int(center_x - 30), int(center_y), label_map.get(face_key, face_key.upper()))
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor(40, 40, 40))
        
        center_x = self.width() // 2
        center_y = self.height() // 2
        size = min(self.width(), self.height()) // 3
        
        import math
        rx = math.radians(self.rotation_x)
        ry = math.radians(self.rotation_y)
        
        vertices = [
            [-1, -1, -1], [1, -1, -1], [1, 1, -1], [-1, 1, -1],
            [-1, -1, 1], [1, -1, 1], [1, 1, 1], [-1, 1, 1]
        ]
        
        projected = []
        for v in vertices:
            x, y, z = v
            x_rot = x * math.cos(ry) - z * math.sin(ry)
            z_rot = x * math.sin(ry) + z * math.cos(ry)
            y_rot = y * math.cos(rx) - z_rot * math.sin(rx)
            z_final = y * math.sin(rx) + z_rot * math.cos(rx)
            scale = size / (3 + z_final)
            projected.append((center_x + x_rot * scale, center_y + y_rot * scale, z_final))
        
        faces = [
            ([0, 1, 2, 3], 'front', QColor(100, 150, 200, 200)),
            ([4, 5, 6, 7], 'back', QColor(80, 120, 180, 200)),
            ([0, 3, 7, 4], 'left', QColor(150, 100, 100, 200)),
            ([1, 2, 6, 5], 'right', QColor(180, 120, 120, 200)),
            ([3, 2, 6, 7], 'top', QColor(100, 180, 100, 200)),
            ([0, 1, 5, 4], 'bottom', QColor(120, 200, 120, 200))
        ]
        
        face_data = []
        for vertex_indices, label, color in faces:
            avg_z = sum(projected[i][2] for i in vertex_indices) / len(vertex_indices)
            face_points = [projected[i] for i in vertex_indices]
            face_data.append((avg_z, face_points, label, color))
        
        for avg_z, face_points, label, color in sorted(face_data, key=lambda x: x[0]):
            self.draw_textured_face(painter, face_points, label, color)
        
        edges = [(0, 1), (1, 2), (2, 3), (3, 0), (4, 5), (5, 6), (6, 7), (7, 4), (0, 4), (1, 5), (2, 6), (3, 7)]
        painter.setPen(QPen(QColor(255, 255, 255, 200), 2))
        for edge in edges:
            p1, p2 = projected[edge[0]], projected[edge[1]]
            painter.drawLine(int(p1[0]), int(p1[1]), int(p2[0]), int(p2[1]))
        
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(10, 20, f"X: {int(self.rotation_x)}° Y: {int(self.rotation_y)}°")
        painter.drawText(10, self.height() - 10, "Drag to rotate")


class CTViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.data = None
        self.current_slice = 0
        self.rotation_x = 0
        self.rotation_y = 0
        self.rotation_z = 0
        self.view_plane = 'axial'
        self.auto_switch_enabled = True
        self.is_recording = False
        self.recorded_frames = []
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle('MRI Viewer')
        self.setGeometry(100, 100, 1600, 900)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_panel.setMaximumWidth(350)
        
        load_btn = QPushButton('Load Volume (.npy / .nii)')
        load_btn.clicked.connect(self.load_file)
        load_btn.setStyleSheet("QPushButton { padding: 10px; font-size: 14px; }")
        left_layout.addWidget(load_btn)
        
        recording_group = QGroupBox("Recording")
        recording_layout = QVBoxLayout()
        self.record_btn = QPushButton('⏺ Start Recording')
        self.record_btn.clicked.connect(self.toggle_recording)
        self.record_btn.setStyleSheet("QPushButton { padding: 10px; font-size: 13px; background-color: #d32f2f; color: white; }")
        recording_layout.addWidget(self.record_btn)
        self.save_video_btn = QPushButton('💾 Save Video')
        self.save_video_btn.clicked.connect(self.save_video)
        self.save_video_btn.setEnabled(False)
        self.save_video_btn.setStyleSheet("QPushButton { padding: 8px; }")
        recording_layout.addWidget(self.save_video_btn)
        self.frame_count_label = QLabel('Frames: 0')
        recording_layout.addWidget(self.frame_count_label)
        recording_group.setLayout(recording_layout)
        left_layout.addWidget(recording_group)
        
        cube_group = QGroupBox("3D Orientation Navigator")
        cube_layout = QVBoxLayout()
        self.cube_navigator = Cube3DNavigator()
        self.cube_navigator.rotation_changed.connect(self.on_cube_rotation_change)
        self.cube_navigator.view_changed.connect(self.on_view_auto_switch)
        cube_layout.addWidget(self.cube_navigator)
        cube_group.setLayout(cube_layout)
        left_layout.addWidget(cube_group)
        
        plane_group = QGroupBox("View Plane")
        plane_layout = QVBoxLayout()
        self.axial_btn = QPushButton('Axial')
        self.sagittal_btn = QPushButton('Sagittal')
        self.coronal_btn = QPushButton('Coronal')
        self.axial_btn.clicked.connect(lambda: self.set_view_plane('axial'))
        self.sagittal_btn.clicked.connect(lambda: self.set_view_plane('sagittal'))
        self.coronal_btn.clicked.connect(lambda: self.set_view_plane('coronal'))
        plane_layout.addWidget(self.axial_btn)
        plane_layout.addWidget(self.sagittal_btn)
        plane_layout.addWidget(self.coronal_btn)
        plane_group.setLayout(plane_layout)
        left_layout.addWidget(plane_group)
        
        slice_group = QGroupBox("Slice Navigation")
        slice_layout = QVBoxLayout()
        slice_controls = QHBoxLayout()
        slice_controls.addWidget(QLabel('Slice:'))
        self.slice_spinbox = QSpinBox()
        self.slice_spinbox.setMinimum(0)
        self.slice_spinbox.setMaximum(0)
        self.slice_spinbox.valueChanged.connect(self.on_spinbox_change)
        slice_controls.addWidget(self.slice_spinbox)
        self.slice_label = QLabel('0 / 0')
        slice_controls.addWidget(self.slice_label)
        slice_layout.addLayout(slice_controls)
        self.slice_slider = QSlider(Qt.Horizontal)
        self.slice_slider.setMinimum(0)
        self.slice_slider.setMaximum(0)
        self.slice_slider.valueChanged.connect(self.on_slice_change)
        slice_layout.addWidget(self.slice_slider)
        slice_group.setLayout(slice_layout)
        left_layout.addWidget(slice_group)
        
        fine_rotation_group = QGroupBox("Fine Rotation Adjustment")
        fine_rotation_layout = QVBoxLayout()
        z_layout = QHBoxLayout()
        z_layout.addWidget(QLabel('In-plane (°):'))
        
        # --- REPLACED SLIDER WITH SPINBOX ---
        self.z_spinbox = QDoubleSpinBox()
        self.z_spinbox.setRange(-360.0, 360.0)
        self.z_spinbox.setValue(0.0)
        self.z_spinbox.setSingleStep(1.0)
        self.z_spinbox.setDecimals(1)
        self.z_spinbox.valueChanged.connect(self.on_fine_rotation_change)
        z_layout.addWidget(self.z_spinbox)
        
        fine_rotation_layout.addLayout(z_layout)
        reset_btn = QPushButton('Reset All Rotations')
        reset_btn.clicked.connect(self.reset_rotation)
        fine_rotation_layout.addWidget(reset_btn)
        fine_rotation_group.setLayout(fine_rotation_layout)
        left_layout.addWidget(fine_rotation_group)
        left_layout.addStretch()
        
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        self.figure = plt.figure(figsize=(12, 10), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        right_layout.addWidget(self.canvas)
        
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        main_layout.addWidget(splitter)
        self.update_plane_buttons()
        
    def on_view_auto_switch(self, view_plane):
        if self.auto_switch_enabled and self.data is not None:
            self.set_view_plane(view_plane)
    
    def set_view_plane(self, plane):
        self.view_plane = plane
        self.update_plane_buttons()
        if self.data is not None:
            self.update_slice_range()
            self.update_display()
    
    def update_plane_buttons(self):
        style_selected = "QPushButton { background-color: #4CAF50; color: white; padding: 8px; font-weight: bold; }"
        style_normal = "QPushButton { padding: 8px; }"
        self.axial_btn.setStyleSheet(style_selected if self.view_plane == 'axial' else style_normal)
        self.sagittal_btn.setStyleSheet(style_selected if self.view_plane == 'sagittal' else style_normal)
        self.coronal_btn.setStyleSheet(style_selected if self.view_plane == 'coronal' else style_normal)
    
    def update_slice_range(self):
        if self.data is None: return
        
        # --- FIXED SLICE RANGES ---
        # Data shape is assumed to be (Z, Y, X)
        if self.view_plane == 'axial':
            num_slices = self.data.shape[0]  # Z axis
        elif self.view_plane == 'coronal':
            num_slices = self.data.shape[1]  # Y axis
        else:  # sagittal
            num_slices = self.data.shape[2]  # X axis
        
        self.slice_slider.setMaximum(num_slices - 1)
        self.slice_spinbox.setMaximum(num_slices - 1)
        self.current_slice = min(self.current_slice, num_slices - 1)
        self.slice_slider.setValue(self.current_slice)
        
    def load_file(self):
        filter_str = 'Medical Image Files (*.npy *.nii *.nii.gz);;NumPy Files (*.npy);;NIfTI Files (*.nii *.nii.gz)'
        filename, _ = QFileDialog.getOpenFileName(self, 'Open Volume', '', filter_str)
        if filename:
            try:
                if filename.endswith('.npy'):
                    self.data = np.load(filename)
                elif filename.endswith(('.nii', '.nii.gz')):
                    if nib is None:
                        QMessageBox.critical(self, "Error", "nibabel library is not installed.")
                        return
                    
                    # --- NIFTI PROCESSING ---
                    img = nib.load(filename)
                    print("Normalizing orientation to RAS...")
                    img = nib.as_closest_canonical(img)
                    
                    print("Resampling to 1x1x1 mm...")
                    img_resampled = resample_to_output(img, voxel_sizes=(1, 1, 1), order=1)
                    data = img_resampled.get_fdata()
                    
                    # Ensure standard (Z, Y, X) orientation
                    if len(data.shape) == 3:
                        data = data.transpose(2, 1, 0)
                    elif len(data.shape) == 4:
                        data = data[:, :, :, 0].transpose(2, 1, 0)
                    self.data = data
                
                print(f"Loaded data shape: {self.data.shape}")
                self.cube_navigator.set_data(self.data)
                self.update_slice_range()
                self.update_display()
            except Exception as e:
                print(f"Error loading file: {e}")
                QMessageBox.critical(self, "Error", f"Failed to load file:\n{str(e)}")
    
    def get_current_slice_data(self):
        if self.data is None: return None
        
        # --- FIXED SLICING LOGIC ---
        if self.view_plane == 'axial':
            return self.data[self.current_slice, :, :]
        elif self.view_plane == 'coronal':
            return self.data[:, self.current_slice, :]
        else:  # sagittal
            return self.data[:, :, self.current_slice]
    
    def apply_rotation(self, img):
        if self.rotation_x == 0 and self.rotation_y == 0 and self.rotation_z == 0:
            return img
        
        rotated = img.copy()
        if self.view_plane == 'axial':
             pass
        elif self.view_plane == 'sagittal':
             rotated = rotate(rotated, 90, reshape=False)
        elif self.view_plane == 'coronal':
             rotated = rotate(rotated, 90, reshape=False)

        if self.rotation_z != 0:
            rotated = rotate(rotated, self.rotation_z, reshape=False, order=1)
        return rotated
    
    def update_display(self):
        if self.data is None: return
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        
        img = self.get_current_slice_data()
        if img is None: return
        
        img = img.copy()
        img = self.apply_rotation(img)
        
        ax.imshow(img, cmap='gray', aspect='auto', interpolation='bilinear')
        
        plane_name = self.view_plane.capitalize()
        if self.view_plane == 'axial':
            total = self.data.shape[0]
            axis_label = f'z={self.current_slice}'
        elif self.view_plane == 'coronal':
            total = self.data.shape[1]
            axis_label = f'y={self.current_slice}'
        else:  # sagittal
            total = self.data.shape[2]
            axis_label = f'x={self.current_slice}'
        
        ax.set_title(f'{plane_name} View ({axis_label}) - Slice {self.current_slice + 1} / {total}', fontsize=14, pad=10)
        ax.axis('off')
        self.figure.tight_layout(pad=2)
        self.canvas.draw()
        self.slice_label.setText(f'{self.current_slice + 1} / {total}')
        
        if self.is_recording:
            self.capture_frame()
    
    def on_slice_change(self, value):
        self.current_slice = value
        self.slice_spinbox.blockSignals(True)
        self.slice_spinbox.setValue(value)
        self.slice_spinbox.blockSignals(False)
        self.update_display()
    
    def on_spinbox_change(self, value):
        self.current_slice = value
        self.slice_slider.blockSignals(True)
        self.slice_slider.setValue(value)
        self.slice_slider.blockSignals(False)
        self.update_display()
    
    def on_cube_rotation_change(self, rx, ry):
        self.rotation_x = rx
        self.rotation_y = ry
        self.update_display()
    
    def on_fine_rotation_change(self):
        self.rotation_z = self.z_spinbox.value()
        self.update_display()
    
    def reset_rotation(self):
        self.cube_navigator.rotation_x = 20
        self.cube_navigator.rotation_y = 30
        self.cube_navigator.update()
        self.z_spinbox.setValue(0)
        self.rotation_x = 0
        self.rotation_y = 0
        self.rotation_z = 0
        self.update_display()
    
    def toggle_recording(self):
        if not self.is_recording:
            self.is_recording = True
            self.recorded_frames = []
            self.record_btn.setText('⏹ Stop Recording')
            self.record_btn.setStyleSheet("QPushButton { padding: 10px; font-size: 13px; background-color: #1976d2; color: white; }")
            self.save_video_btn.setEnabled(False)
            self.frame_count_label.setText('Frames: 0 | Recording...')
        else:
            self.is_recording = False
            self.record_btn.setText('⏺ Start Recording')
            self.record_btn.setStyleSheet("QPushButton { padding: 10px; font-size: 13px; background-color: #d32f2f; color: white; }")
            self.save_video_btn.setEnabled(len(self.recorded_frames) > 0)
            self.frame_count_label.setText(f'Frames: {len(self.recorded_frames)} | Ready to save')
    
    def capture_frame(self):
        pixmap = self.canvas.grab()
        qimage = pixmap.toImage()
        width = qimage.width()
        height = qimage.height()
        ptr = qimage.bits()
        ptr.setsize(qimage.byteCount())
        arr = np.array(ptr).reshape(height, width, 4)
        frame = arr[:, :, :3].copy()
        self.recorded_frames.append(frame)
        self.frame_count_label.setText(f'Frames: {len(self.recorded_frames)} | Recording...')
    
    def save_video(self):
        if len(self.recorded_frames) == 0: return
        filename, _ = QFileDialog.getSaveFileName(self, 'Save Video', 'ct_recording.mp4', 'Video Files (*.mp4 *.avi);;All Files (*)')
        if not filename: return
        try:
            import cv2
            height, width = self.recorded_frames[0].shape[:2]
            fourcc = cv2.VideoWriter_fourcc(*'XVID') if filename.endswith('.avi') else cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(filename, fourcc, 30.0, (width, height))
            for frame in self.recorded_frames:
                out.write(cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
            out.release()
            self.frame_count_label.setText(f'✓ Saved {len(self.recorded_frames)} frames')
        except ImportError:
            self.frame_count_label.setText('Error: opencv-python not installed')
        except Exception as e:
            self.frame_count_label.setText(f'Error saving video')

if __name__ == '__main__':
    app = QApplication(sys.argv)
    viewer = CTViewer()
    viewer.show()
    sys.exit(app.exec_())
