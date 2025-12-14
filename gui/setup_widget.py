from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QCheckBox, QGroupBox, QFileDialog, QLineEdit, 
                             QSizePolicy, QSlider, QProgressDialog, QMessageBox,
                             QColorDialog, QComboBox) 
from PyQt6.QtCore import Qt, pyqtSlot, pyqtSignal
from PyQt6.QtGui import QColor, QPixmap, QImage 
from .video_widget import VideoWidget
from .overlay_widgets import AnalysisOverlay
# from .ai_thread import AIWorker # AIWorker is now managed by MainWindow

class SetupWidget(QWidget):
    analyze_video_signal = pyqtSignal(str, dict) # Signal to start analysis in MainWindow

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        
        self.shot_colors = {
            "Good": QColor("#4CAF50"), 
            "Bad": QColor("#FF9800"),  
            "Out": QColor("#F44336")   
        }
        
        # self.ai_worker = None # AIWorker is now managed by MainWindow
        self.init_ui()

    def init_ui(self):
        main_layout = QHBoxLayout()

        # [Left] Video Area
        video_container = QWidget()
        video_layout = QVBoxLayout(video_container)
        video_layout.setContentsMargins(0, 0, 0, 0)

        load_layout = QHBoxLayout()
        self.path_label = QLineEdit("Select a video file...")
        self.path_label.setReadOnly(True)
        btn_load = QPushButton("📂 Load Video")
        btn_load.clicked.connect(self.load_video_file)
        load_layout.addWidget(self.path_label)
        load_layout.addWidget(btn_load)

        self.preview_player = VideoWidget()
        self.preview_player.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        video_layout.addLayout(load_layout)
        video_layout.addWidget(self.preview_player, 1) # Set stretch factor to 1

        # Overlay Init
        self.analysis_overlay = AnalysisOverlay(self.preview_player.screen)
        self.analysis_overlay.move(50, 50) # This overlay is for setup/preview only

        # [Right] Settings Panel
        right_panel = QVBoxLayout()
        
        # 1. Court Type (단식/복식 선택)
        group_court = QGroupBox("Court Settings")
        layout_court = QVBoxLayout()
        self.combo_court_type = QComboBox()
        self.combo_court_type.addItems(["Singles (단식)", "Doubles (복식)"])
        layout_court.addWidget(QLabel("Match Type:"))
        layout_court.addWidget(self.combo_court_type)
        group_court.setLayout(layout_court)

        # 2. Opacity Slider & Colors
        group_opacity = QGroupBox("Overlay Settings")
        layout_opacity = QVBoxLayout()
        
        self.slider_opacity = QSlider(Qt.Orientation.Horizontal)
        self.slider_opacity.setRange(10, 100); self.slider_opacity.setValue(80)
        self.slider_opacity.valueChanged.connect(self.change_opacity)
        
        layout_opacity.addWidget(QLabel("Transparency:"))
        layout_opacity.addWidget(self.slider_opacity)
        
        # Colors
        layout_opacity.addWidget(QLabel("Shot Analysis Colors:"))
        self.btn_color_good = self.create_color_btn("Good Shot (In)", "Good")
        self.btn_color_bad = self.create_color_btn("Bad Shot (Hazard)", "Bad")
        self.btn_color_out = self.create_color_btn("Real Out (Out)", "Out")
        
        layout_opacity.addWidget(self.btn_color_good)
        layout_opacity.addWidget(self.btn_color_bad)
        layout_opacity.addWidget(self.btn_color_out)
        
        group_opacity.setLayout(layout_opacity)

        # 3. AI Options
        group_ai = QGroupBox("AI Features")
        layout_ai = QVBoxLayout()
        self.chk_ball = QCheckBox("Ball Tracking"); self.chk_ball.setChecked(True)
        self.chk_pose = QCheckBox("Pose Estimation")
        self.chk_bounce = QCheckBox("Bounce Map"); self.chk_bounce.setChecked(True)
        layout_ai.addWidget(self.chk_ball); layout_ai.addWidget(self.chk_pose); layout_ai.addWidget(self.chk_bounce)
        group_ai.setLayout(layout_ai)

        # 4. Convert Button
        self.btn_convert = QPushButton("START AI ANALYSIS")
        self.btn_convert.setFixedHeight(60)
        self.btn_convert.setStyleSheet("background-color: #FF5722; color: white; font-weight: bold; font-size: 16px; border-radius: 8px;")
        self.btn_convert.clicked.connect(self.start_conversion)

        # 패널 배치 순서
        right_panel.addWidget(group_court)
        right_panel.addWidget(group_opacity)
        right_panel.addWidget(group_ai)
        right_panel.addStretch()
        right_panel.addWidget(self.btn_convert)

        main_layout.addWidget(video_container, stretch=3)
        main_layout.addLayout(right_panel, stretch=1)
        self.setLayout(main_layout)

    def mousePressEvent(self, event):
        # Deselect the overlay if the click is outside of it
        if not self.analysis_overlay.geometry().contains(event.pos()):
            self.analysis_overlay.deselect()
        super().mousePressEvent(event)

    def create_color_btn(self, text, key):
        btn = QPushButton(text)
        col = self.shot_colors[key]
        btn.setStyleSheet(f"background-color: {col.name()}; color: white; font-weight: bold; border: 1px solid #555;")
        btn.clicked.connect(lambda: self.open_color_picker(btn, key))
        return btn

    def open_color_picker(self, btn, key):
        color = QColorDialog.getColor(self.shot_colors[key], self, f"Select Color for {key}")
        if color.isValid():
            self.shot_colors[key] = color
            btn.setStyleSheet(f"background-color: {color.name()}; color: white; font-weight: bold;")
            self.analysis_overlay.update_colors(key, color)

    def load_video_file(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Open Video", "", "Video Files (*.mp4 *.avi *.mov *.mkv)")
        if file_name:
            self.path_label.setText(file_name)
            self.preview_player.load_video(file_name)
            self.preview_player.setFocus() 

    def change_opacity(self, value):
        # This overlay is for setup/preview only. The actual analysis overlay will be drawn in VideoWidget
        # self.analysis_overlay.set_opacity_value(value) 
        pass
        
    def start_conversion(self):
        video_path = self.path_label.text()
        if not video_path or "Select" in video_path:
            QMessageBox.warning(self, "Warning", "Please load a video first!")
            return

        # Prepare settings dictionary
        settings = {
            'court_type': self.combo_court_type.currentText().split(' ')[0], # Singles or Doubles
            'show_ball': self.chk_ball.isChecked(),
            'show_pose': self.chk_pose.isChecked(),
            'colors': {k: v.name() for k, v in self.shot_colors.items()} # Pass color names
        }
        
        self.analyze_video_signal.emit(video_path, settings) # Emit signal to MainWindow
        # MainWindow will call switch_to_result_tab()
    
    # Removed AIWorker related slots, as MainWindow will manage the AIWorker
    # @pyqtSlot(QImage) 
    # def update_result_image(self, qt_img):
    #     pass
    
    # @pyqtSlot(float, float)
    # def update_ball_position(self, x, y):
    #     pass

    # @pyqtSlot(list) 
    # def update_bounce_history(self, history_list: list):
    #     pass

    # def analysis_finished(self):
    #     QMessageBox.information(self, "Done", "AI Analysis Completed!")