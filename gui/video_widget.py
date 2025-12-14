import cv2
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QSlider, QPushButton, QStyle, QSizePolicy, QMessageBox)
from PyQt6.QtCore import Qt, QTimer, QUrl, QEvent, QPointF, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap, QPainter, QColor, QFont
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from .volume_control import VolumeControlWidget

import cv2
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QSlider, QPushButton, QStyle, QSizePolicy)
from PyQt6.QtCore import Qt, QTimer, QUrl, QEvent, QPointF, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap, QPainter, QColor, QFont
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from .volume_control import VolumeControlWidget

class VideoWidget(QWidget):
    frame_to_process_signal = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        
        self.cap = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.next_frame)
        self.is_playing = False
        self.total_frames = 0
        self.fps = 30

        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(0.5)
        
        self.bounce_history = []
        
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.screen = QLabel()
        self.screen.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.screen.setStyleSheet("background-color: black;")
        self.screen.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.screen.setMinimumHeight(400)
        self.display_text("No Video")
        
        controls_layout = QHBoxLayout()
        
        self.btn_play = QPushButton()
        self.btn_play.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self.btn_play.clicked.connect(self.toggle_play)
        
        btn_prev = QPushButton("-10s")
        btn_prev.clicked.connect(lambda: self.seek_relative(-10))
        btn_next = QPushButton("+10s")
        btn_next.clicked.connect(lambda: self.seek_relative(10))

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 0)
        self.slider.sliderPressed.connect(self.pause_video)
        self.slider.sliderReleased.connect(self.resume_video)
        self.slider.sliderMoved.connect(self._set_media_player_position)

        self.volume_control = VolumeControlWidget(self.audio_output)
        
        controls_layout.addWidget(self.btn_play)
        controls_layout.addWidget(btn_prev)
        controls_layout.addWidget(self.slider)
        controls_layout.addWidget(btn_next)
        controls_layout.addStretch()
        controls_layout.addWidget(self.volume_control)

        layout.addWidget(self.screen)
        layout.addLayout(controls_layout)
        
        self.enable_controls(False)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Space:
            self.toggle_play()
        elif event.key() == Qt.Key.Key_Left:
            self.seek_relative(-2)
        elif event.key() == Qt.Key.Key_Right:
            self.seek_relative(2)
        else:
            super().keyPressEvent(event)

    def enable_controls(self, enable):
        self.btn_play.setEnabled(enable)
        self.slider.setEnabled(enable)
        self.volume_control.setEnabled(enable)

    def display_text(self, text):
        self.screen.setText(f"<span style='color:white; font-size:20px;'>{text}</span>")

    def load_video(self, file_path):
        self.display_text("Loading...")
        
        if self.cap: self.cap.release()
        self.cap = cv2.VideoCapture(file_path)
        if not self.cap.isOpened():
            self.display_text("Failed to Load Video")
            return

        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        if self.fps == 0: self.fps = 30
        
        self.media_player.setSource(QUrl.fromLocalFile(file_path))
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.slider.setRange(0, self.total_frames)
        
        self.enable_controls(True)
        self.setFocus()
        self.next_frame()

    def next_frame(self):
        if not self.cap or not self.cap.isOpened(): return
        
        ret, frame = self.cap.read()
        if ret:
            # Emit the raw frame for background processing
            self.frame_to_process_signal.emit(frame.copy())
            
            # Immediately display the raw frame to ensure real-time playback
            rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            qt_image = QImage(rgb_image.data, w, h, ch * w, QImage.Format.Format_RGB888)
            
            # Draw bounce history on the QImage before displaying
            painter = QPainter(qt_image)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            for bounce_x, bounce_y, result_type in self.bounce_history:
                x_pixel = int(bounce_x * w)
                y_pixel = int(bounce_y * h)
                
                color_map = {'Good': QColor(0, 255, 0), 'Out': QColor(255, 0, 0), 'Net': QColor(255, 255, 0)}
                color = color_map.get(result_type, QColor("gray"))
                painter.setBrush(color)
                painter.setPen(color)
                painter.drawEllipse(QPointF(x_pixel, y_pixel), 5, 5)
            painter.end()

            scaled_pixmap = QPixmap.fromImage(qt_image).scaled(
                self.screen.size(), 
                Qt.AspectRatioMode.KeepAspectRatio, 
                Qt.TransformationMode.SmoothTransformation
            )
            self.screen.setPixmap(scaled_pixmap)

            if not self.slider.isSliderDown():
                self.slider.setValue(int(self.cap.get(cv2.CAP_PROP_POS_FRAMES)))
        else:
            self.pause_video()
            
    def update_analysis_data(self, stats: dict):
        """Receives analysis results asynchronously and stores them."""
        self.bounce_history = stats.get('bounce_history', [])

    def toggle_play(self):
        if self.is_playing:
            self.pause_video()
        else:
            self.play_video()

    def play_video(self):
        if self.cap:
            self.is_playing = True
            self.timer.start(int(1000 / self.fps))
            self.btn_play.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPause))
            self.media_player.play()

    def pause_video(self):
        self.is_playing = False
        self.timer.stop()
        self.btn_play.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self.media_player.pause()
    
    def resume_video(self):
        if not self.is_playing:
            self.play_video()

    def _set_media_player_position(self, frame_idx):
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        self.media_player.setPosition(int(frame_idx / self.fps * 1000))
        self.next_frame()

    def _sync_media_player_position(self):
        if not self.slider.isSliderDown() and self.is_playing:
            current_frame = int(self.media_player.position() / 1000 * self.fps)
            self.slider.setValue(current_frame)
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, current_frame)

    def seek_relative(self, seconds):
        if self.cap:
            curr_frame = self.cap.get(cv2.CAP_PROP_POS_FRAMES)
            target_frame = max(0, min(curr_frame + (seconds * self.fps), self.total_frames))
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
            self.slider.setValue(int(target_frame))
            self.media_player.setPosition(int(target_frame / self.fps * 1000))
            self.next_frame()
